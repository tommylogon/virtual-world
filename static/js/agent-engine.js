"use strict";
/**
 * AgentEngine - Character agent loop, turn management, and LLM orchestration
 * With thought->act->react, rest-skip, rate limiter, planning, and memory reflection
 *
 * @module agent-engine - the character agent loop and turn management
 * @contributes AgentEngine: per-character step pipeline, phases, planning, reflection, abort
 * @powers Turn queue, NPC behaviour - autonomous character turns and the Run / Step once / Cancel controls
 * @relates uses llm-client + api + agent/prompt-builder; supports human-turn-composer
 * @docs docs/virtualWorld/AI & Narration/Agent Engine.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
const NOOP_VERBS = ['wait', 'nothing', 'pause', 'stay'];
// task-104: after a SUCCESSFUL action, the agent may chain ONE immediate
// follow-up from the verb list (same-turn, like the original dash chain).
// The LLM answers a quick decision prompt; invalid picks are discarded.
const CHAIN_RULES = {
    dash: ['go', 'wait'],
    lead: ['go', 'approach', 'release', 'wait'],
    // A grab buys a same-turn *single* move, so a character can seize someone and
    // drag them one area (out of danger, or into the dark) - `movement.py` drags
    // grappled targets via `grapple.drag_all`. `dash` is deliberately NOT here:
    // grab + two-area dash is overpowered. Matches `lead`, which allows `go` only.
    grab: ['go', 'approach', 'release', 'wait'],
};
const agentConfig = config;
/** globals.d.ts narrows ApiClient to the calls converted code made; these are more. */
const agentApi = ApiClient;
/** Read late, not captured at load: narration-ui.js is a separate script tag. */
const agentNarrationUI = () => window.narrationUI;
/** Possessive pronoun for a character, from its identity tags (female/male). */
function _possessivePronoun(name) {
    const tags = (worldState.players?.[name]?.tags) || [];
    if (tags.includes('female') || tags.includes('woman') || tags.includes('girl'))
        return 'her';
    if (tags.includes('male') || tags.includes('man') || tags.includes('boy'))
        return 'his';
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
        this.contextMgr = new window.ContextWindowManager({ maxTokens: 9500, maxMessages: 30, recentTurnCount: 6, criticalContextRetention: true });
        this._rateLimiter = new window.RateLimiter();
        this._stepping = false;
        this._cancelRequested = false;
        this._abortController = null;
        // task-101 experimental simultaneous modes: per-character act
        // countdowns (global), and per-room countdowns (simultaneous_room).
        this._simCountdowns = {};
        this._simRoomCountdowns = {};
        this._simDeadlines = {};
        this._paused = false;
        this._pausedAt = null;
        this._resumeAfterVisibility = false;
        // task-166: per-character startle tracking. `_startleSeen` remembers
        // which hearing entries already startled a character (so a shout does
        // not yelp on every line forever); `_startleCache` lets the speech and
        // the emote of the same turn agree, and resets each turn.
        this._startleSeen = {};
        this._startleCache = {};
        this._startleCacheTurn = -1;
    }
    get isPaused() { return this._paused; }
    getHistory(charName) {
        if (!this.characterHistories[charName]) {
            const player = worldState.data?.players?.[charName];
            this.characterHistories[charName] = [{ role: 'system', content: PromptBuilder.buildCharacterSystemPrompt(charName, player, config.softMaxTokens) }];
        }
        return this.characterHistories[charName];
    }
    getDisplayHistory(charName) { return this.getHistory(charName).slice(1); }
    /** Fix 8: centralized controllingPlayer resolution - used by step, stepOnce, start */
    _resolveControllingPlayer() {
        return config.controllingPlayer
            || worldState.data?.active_player
            || (config.turnBased ? TurnQueue.getCurrentCharacter() : undefined)
            || undefined;
    }
    /** Current graph area node id for a character (entity link for memories). */
    _currentAreaEntityId(charName) {
        const player = worldState.runtimePlayer(charName);
        if (player?.current_area_id)
            return player.current_area_id;
        const area = player?.current_area;
        if (!area)
            return '';
        return `area_${String(area).toLowerCase().replace(/\s+/g, '_')}`;
    }
    /**
     * task-166: did a NEW sudden loud sound just land on this character?
     * Reads `recent_hearing` (task-248/306) for shout/scream entries the
     * character has not been startled by yet. The result is cached for the
     * turn so a character's speech and emote share one startle.
     */
    _detectStartle(charName, player) {
        if (!charName)
            return false;
        if (this._startleCacheTurn !== this.turnNumber) {
            this._startleCache = {};
            this._startleCacheTurn = this.turnNumber;
        }
        if (charName in this._startleCache)
            return this._startleCache[charName];
        if (!this._startleSeen[charName])
            this._startleSeen[charName] = new Set();
        const seen = this._startleSeen[charName];
        const hearing = player?.recent_hearing || [];
        const live = new Set();
        let startled = false;
        for (const h of hearing) {
            if (!h)
                continue;
            const key = `${h.tick ?? ''}|${h.speaker ?? ''}|${h.text ?? ''}|${h.speech_level ?? ''}`;
            live.add(key);
            if (seen.has(key))
                continue;
            if (h.speech_level === 'shout' || h.speech_level === 'scream')
                startled = true;
        }
        // Keep only entries still in the live buffer so the set stays bounded.
        this._startleSeen[charName] = live;
        this._startleCache[charName] = startled;
        return startled;
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
        return window.PlanManager.generate(charName);
    }
    async reflect(charName) {
        await window.AgentMemory.reflect(charName);
    }
    _checkCancel() {
        if (!this._cancelRequested)
            return false;
        this._cancelRequested = false;
        if (this._abortController) {
            this._abortController.abort();
            this._abortController = null;
        }
        config.busy = false;
        VW?.ui?.updateButtons();
        VW?.ui?.stopRateLimitMonitor();
        events.log("⏹️ Step cancelled.", "system-msg");
        VW?.ui?.showPlayPause(true, false);
        return true;
    }
    cancel() {
        this._cancelRequested = true;
        if (this._abortController) {
            this._abortController.abort();
            this._abortController = null;
        }
        config.busy = false;
        config.running = false;
        this._paused = false;
        this._pausedAt = null;
        this._resumeAfterVisibility = false;
        VW?.ui?.updateButtons();
        VW?.ui?.stopRateLimitMonitor();
        VW?.ui?.setStatus("Cancelled.", "info");
        VW?.ui?.showPlayPause(true, false);
    }
    /** Common turn-end cleanup: log, clear busy, advance queue if needed. */
    async _endTurnEarly(logMsg, logClass = 'system-msg') {
        if (logMsg)
            events.log(logMsg, logClass);
        config.busy = false;
        VW?.ui?.updateButtons();
        if (config.running && config.turnBased && this.turnQueue.length > 0) {
            await TurnQueue.advance();
            if (worldState.data)
                VW?.ui?.renderAll(worldState.data);
        }
    }
    /**
     * Surface a character's freshly generated turn events (from the last
     * endTurn fetch) on the main stream.
     *
     * The 👾 lines are the SOLE surfacing mechanism for simple NPCs (they have
     * no dedicated thought/speech/action logging). LLM agents + humans already
     * surface everything through their own paths - thoughts, speech, action
     * results, emotes - and the backend ALSO records speak/emote as turn_events
     * for them, so re-logging here would double-post. Therefore only simple
     * NPCs ever get 👾 output.
     */
    _logActorTurnEvents(charName) {
        if (!charName)
            return false;
        const freshState = worldState.data;
        if (!freshState?.players?.[charName]?.simple_npc)
            return false;
        const npcEvents = (freshState?.turn_events || []).filter((evt) => evt.actor === charName);
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
        const spokenVolume = volume || 'say';
        events.trackPhase(charName, 'speech', { speech, volume: spokenVolume, target });
        events.trackAction(charName, null, speech, null, '');
        // task-166: involuntary interruptions (hiccups, stutters, coughs) -
        // flavor only, never replaces the intended line. Runs BEFORE the text
        // is sent so the room and event stream both see the injected moment.
        // A sudden loud sound this turn raises a yelp (startle).
        const startled = this._detectStartle(charName, player);
        const injected = window.Involuntary?.speech ? window.Involuntary.speech(speech, player, { startled }) : null;
        if (injected)
            speech = injected;
        // Directed whisper (task-248): "whisper to <name>: text" reaches only
        // the target; the rest of the room sees the gesture, not the words.
        const directed = spokenVolume === 'whisper' && target;
        const command = directed ? `whisper to ${target}: ${speech}` : `${spokenVolume} ${speech}`;
        try {
            const data = await agentApi.action(command, charName);
            const output = (data && data.output) || '';
            const blocked = (data && data.success === false) ||
                /no sound comes out|can't move or act|can't do that/i.test(output);
            if (blocked) {
                events.log(`🔇 ${player.name}: ${output.trim() || 'cannot speak.'}`, 'error-msg');
            }
            else if (directed) {
                // task-340: whispered lines get a distinct locked row in the stream.
                events.log(`🔒 ${player.name} → ${target}: "${speech}"`, "msg-whisper");
            }
            else {
                events.log(`[${player.name}] ${ActionNormalizer.volVerb(spokenVolume)}: "${speech}"`, "msg-speech");
            }
        }
        catch (err) {
            events.log(`[${player.name}] ${ActionNormalizer.volVerb(spokenVolume)}: "${speech}"`, "msg-speech");
        }
    }
    async _performEmote(charName, emote) {
        try {
            // task-166: involuntary emote tail (a hiccup, a yelp, a shiver).
            const player = worldState.runtimePlayer(charName);
            const startled = this._detectStartle(charName, player);
            const injected = window.Involuntary?.emote ? window.Involuntary.emote(emote, player, { startled }) : null;
            if (injected)
                emote = injected;
            const emoteResult = await agentApi.emote(charName, emote);
            if (emoteResult?.description) {
                events.log(emoteResult.description, 'msg-emote');
                events.trackAction(charName, '', null, `emote: ${emote}`, emoteResult.description);
            }
        }
        catch (emoteErr) {
            events.log(`Emote error: ${emoteErr instanceof Error ? emoteErr.message : String(emoteErr)}`, 'error-msg');
        }
    }
    _storeReactionMemory(charName, memory, feltEmotion = null, actionSucceeded = true, actionResult = '') {
        if (!memory?.text)
            return;
        // Fix #7: reject memories that claim success for a failed action.
        if (!actionSucceeded) {
            const lower = memory.text.toLowerCase();
            const successClaims = ['succeeded', 'worked', 'managed to', 'was able to', 'accomplished', 'achieved', 'completed', 'finished', 'done', 'lit', 'ignited', 'started', 'opened', 'unlocked', 'found', 'discovered', 'revealed'];
            if (successClaims.some(claim => lower.includes(claim))) {
                events.log(`⚠️ ${charName} memory rejected: claims success for failed action`, 'error-msg');
                return;
            }
        }
        const entityId = this._currentAreaEntityId(charName);
        const tick = worldState.runtimeData?.time_ticks ?? worldState.data?.time_ticks ?? 0;
        const normalized = memory.text.trim().toLowerCase();
        const player = worldState.runtimePlayer(charName);
        const duplicate = (player?.memories || []).some((existing) => {
            const sameText = (existing.text || '').trim().toLowerCase() === normalized;
            const sameTick = Math.abs((existing.tick || 0) - tick) <= 1;
            return sameText && sameTick;
        });
        if (duplicate)
            return;
        window.AgentMemory.storeMemory(charName, memory.text, memory.importance, 'reaction', tick, entityId ? [entityId] : [], memory.tags, feltEmotion, memory.emotions || null);
    }
    /**
     * Fire-and-forget spike of the character's affect map from an LLM-declared
     * feeling (task-96). Silent no-op when absent/malformed or backend misses.
     */
    _applyFeltEmotion(charName, emotion) {
        if (!emotion?.label || !worldState.players?.[charName])
            return null;
        // task-350: when the feeling is TOWARD a specific person, pass `toward`
        // so the backend records it as an experience (felt_toward) and so
        // relationships/feelings can change toward that person. Otherwise it's
        // a global affect spike (legacy).
        const body = { emotion: emotion.label, intensity: Math.max(1, Math.min(10, emotion.intensity)) };
        if (emotion.toward)
            body.toward = emotion.toward;
        else
            body.delta = body.intensity * 1.5;
        try {
            return fetch(`/api/players/${encodeURIComponent(charName)}/emotions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            }).catch(() => { });
        }
        catch (e) {
            return null;
        }
    }
    /** task-350: record names the agent confirmed/deduced this turn (heard,
     *  name tag, sign, document, deduction). Fire-and-forget; engine validates
     *  they are real present players so the agent cannot invent a name tag. */
    _learnNames(charName, learnedNames) {
        if (!learnedNames?.length || !worldState.players?.[charName])
            return;
        try {
            return fetch(`/api/players/${encodeURIComponent(charName)}/names`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ names: learnedNames })
            }).catch(() => { });
        }
        catch (e) {
            return null;
        }
    }
    /**
     * Human turn: pause the run loop and let the human compose their turn
     * through the scene-first panel (task-333). Mirrors the agent loop's
     * think→act→react shape (task-334): compose → act → act … → react →
     * pass. Execution rides the SAME pipeline an agent uses (_speakLine /
     * ApiClient.action / _performEmote / _storeReactionMemory). Targets the
     * character via setActivePlayer for clean multi-human handoff (task-245).
     */
    async _humanTurn(charName) {
        let player = worldState.players?.[charName];
        if (!player) {
            await worldState.fetch();
            player = worldState.players?.[charName];
        }
        if (!player?.id) {
            events.log(`⚠️ Human character "${charName}" not found.`, 'error-msg');
            return this._endTurnEarly(null);
        }
        worldState.setRuntimeFocus([player.id]);
        try {
            await agentApi.setActivePlayer(charName);
            await worldState.fetchRuntime();
            const state = worldState.runtimeData;
            player = state?.players?.[charName] || player;
            if (!state || !state.players?.[charName]) {
                events.log(`⚠️ Focused runtime state omitted "${charName}".`, 'error-msg');
                return this._endTurnEarly(null);
            }
            if (state.scenario_ended) {
                events.log("🏁 Scenario ended via trigger.", "system-msg");
                if (state._restart_requested) {
                    events.log("🔄 Restarting scenario...", "system-msg");
                    await agentApi.resetWorld();
                    events.log("✅ Scenario restarted.", "system-msg");
                    return;
                }
                this.stop();
                return;
            }
            let reply = await HumanTurnComposer.request(charName, { first: true });
            if (config.running && config.turnBased && this.turnQueue.length === 0) {
                this.stop();
                return;
            }
            const results = [];
            // task-352: the human turn is a CONTINUOUS loop in one panel - act, the
            // world answers, act again, until the player Ends or the budget empties.
            // Stop on the first failed action. The turn ends with ONE applyTurn
            // (TurnQueue.advance below), never one per step.
            while (reply && !reply.endTurn && reply.step) {
                const currentPlayer = worldState.runtimePlayer(charName) || player;
                const step = reply.step;
                const res = await this._executeHumanReply(charName, currentPlayer, step);
                if (res.text)
                    results.push(res.text);
                await worldState.fetchRuntime();
                const currentArea = worldState.runtimePlayer(charName)?.current_area;
                if (currentArea)
                    agentConfig.lastRoom[charName] = currentArea;
                if (step.memory?.text)
                    this._storeReactionMemory(charName, step.memory);
                // Deterministic auto-memory: one instant, LLM-free line per action.
                const areaName = worldState.runtimePlayer(charName)?.current_area || '';
                const memoryBits = [
                    step.action ? `did ${step.action}` : '',
                    step.speech ? `said "${step.speech}"` : '',
                ].filter(Boolean).join(' and ');
                if (memoryBits) {
                    this._storeReactionMemory(charName, {
                        text: `${memoryBits} (${areaName}, tick ${worldState.runtimeData?.time_ticks ?? worldState.tick})`,
                        importance: 4,
                    });
                }
                if (res.success === false)
                    break;
                // bug-544: break only on a PUBLISHED budget that is exhausted. An
                // empty `turn_slots` (`{}`) is the "not started" sentinel the engine
                // lazily fills; treating it as spent ended the human turn after one
                // step and refused the next action.
                const slots = worldState.runtimePlayer(charName)?.turn_slots;
                const spentOut = !!slots && Object.keys(slots).length > 0
                    && !Object.values(slots).some((n) => n > 0);
                if (spentOut)
                    break;
                reply = await HumanTurnComposer.request(charName, { lastResult: res.text });
            }
            const endedByPlayer = !!(reply && reply.endTurn);
            if (!results.length) {
                events.log(`🔜 ${charName} passed ${_possessivePronoun(charName)} turn.`, 'system-msg');
            }
            else if (!endedByPlayer) {
                // task-334 lane 1: one closing react beat - the player's answer to
                // what actually happened, and where outcome-grounded memory lands.
                const reaction = await HumanTurnComposer.react(charName, results);
                if (reaction && !reaction.endTurn) {
                    const currentPlayer = worldState.runtimePlayer(charName) || player;
                    if (reaction.speech) {
                        await this._speakLine(charName, currentPlayer, reaction.speech, reaction.volume, reaction.target);
                    }
                    if (reaction.emote) {
                        await this._performEmote(charName, reaction.emote);
                    }
                    if (reaction.memory?.text) {
                        this._storeReactionMemory(charName, reaction.memory);
                    }
                }
            }
            HumanTurnComposer.closeTurn();
            // Turn handoff is a turn-based concept (task-333 browser-test fix):
            // outside turn-based mode the human keeps control - no roster
            // rotation, the run loop just continues from here.
            if (config.running && config.turnBased && this.turnQueue.length > 0) {
                await TurnQueue.advance();
            }
            // Keep the focused client cache current after the tick without
            // serializing and transferring the unrelated world.
            await worldState.fetchRuntime();
        }
        catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            events.log(`Focused runtime state failed: ${message}`, 'error-msg');
            throw error;
        }
        finally {
            worldState.setRuntimeFocusForCharacter(config.controllingPlayer || charName);
        }
    }
    /**
     * Execute one human reply (speech → action → emote) through the agent
     * pipeline. Returns the action's result text (for the react phase).
     */
    async _executeHumanReply(charName, player, reply) {
        // bug-33: a human turn has no agent phase marker to open the card, so
        // open it here before speech/emote rows are emitted - otherwise they
        // land in the bare stream above the next `act` phase marker.
        events.beginActorTurn(charName);
        if (reply.speech) {
            await this._speakLine(charName, player, reply.speech, reply.speechVolume, reply.target);
        }
        // task-xxx: emote renders before the action result (consistent with the
        // agent decide phase) so the stream reads gesture → outcome.
        if (reply.emote) {
            await this._performEmote(charName, reply.emote);
        }
        let resultText = '';
        let success = true;
        if (reply.action) {
            events.logPhase(charName, 'act', reply.action);
            if (!reply.action.startsWith('speak '))
                events.log(`[Action] ${reply.action}`, "msg-action");
            try {
                const data = await agentApi.action(reply.action, charName, { enforceSlots: true });
                if (data?.scenario_ended) {
                    events.log("🏁 Scenario ended via trigger.", "system-msg");
                    if (data?._restart_requested) {
                        events.log("🔄 Restarting scenario...", "system-msg");
                        await agentApi.resetWorld();
                        await worldState.fetch();
                        events.log("✅ Scenario restarted.", "system-msg");
                        VW?.ui?.renderAll?.(worldState.data);
                    }
                }
                else {
                    const output = data?.output || '';
                    success = data?.success !== false;
                    if (data?.system_messages) {
                        data.system_messages.forEach((systemMessage) => events.log(systemMessage, 'system-msg'));
                    }
                    if (output && !output.includes('says:')) {
                        if (output.includes('ValueError'))
                            events.log(output, 'error-msg');
                        else
                            events.log(output, 'msg-result', { outcome: data?.success !== false ? 'success' : 'failure' }, charName);
                    }
                    // task-448: an ambiguous target returns a structured chooser;
                    // render it so a pick resolves to the identity key.
                    if (Array.isArray(data?.choices)) {
                        for (const group of data.choices) {
                            events.logChoices(group.verb, group.options, charName);
                        }
                    }
                    agentConfig.lastActionResult[charName] = output;
                    events.trackAction(charName, '', null, reply.action, output);
                    resultText = output;
                }
            }
            catch (err) {
                const errMsg = err instanceof Error ? err.message : String(err);
                events.log(`Action error: ${errMsg}`, 'error-msg');
                resultText = errMsg;
                success = false;
            }
        }
        return { text: resultText, success };
    }
    async step() {
        if (this._checkCancel())
            return;
        config.busy = true;
        // config.controllingPlayer is client-only and not persisted, but the
        // header's "Active:" comes from the server's active_player - so after a
        // refresh they disagree. Fall back to the server's active player rather
        // than refusing to run with "no agent selected".
        let charName = this._resolveControllingPlayer();
        if (charName)
            config.controllingPlayer = charName;
        if (config.turnBased && this.turnQueue.length === 0)
            TurnQueue.initialize();
        if (config.turnBased && this.turnQueue.length === 0) {
            config.running = false;
            config.busy = false;
            VW?.ui?.updateButtons();
            VW?.ui?.showPlayPause(true, false);
            VW?.ui?.setStatus("Stopped.", "error");
            events.log("⏹️ All dead.", "system-msg");
            this.stop();
            return;
        }
        if (config.turnBased && this.turnQueue.length > 0) {
            const ctc = TurnQueue.getCurrentCharacter();
            if (ctc && charName !== ctc)
                charName = ctc;
        }
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
            }
            finally {
                config.busy = false;
                VW?.ui?.updateButtons();
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
            config.busy = false;
            VW?.ui?.updateButtons();
            VW?.ui?.setStatus("Idle.", "info");
            return this._endTurnEarly("⚠️ No agent selected. Click an agent in the list first.", "system-msg");
        }
        let history = this.getHistory(charName);
        if (!agentConfig.lastActionResult[charName])
            agentConfig.lastActionResult[charName] = '';
        VW?.ui?.setStatus("Thinking...", "info");
        worldState.setRuntimeFocusForCharacter(charName);
        try {
            if (!config.apiKey && !config.apiBase?.includes('localhost') && !config.apiBase?.includes('127.0.0.1')) {
                events.log("No API key.", "error-msg");
                config.running = false;
                VW?.ui?.updateButtons();
                return;
            }
            if (!config.model) {
                events.log("No model.", "error-msg");
                config.running = false;
                VW?.ui?.updateButtons();
                return;
            }
            if (!config.controllingPlayer) {
                events.log("No char.", "error-msg");
                config.running = false;
                VW?.ui?.updateButtons();
                return;
            }
            await agentApi.setActivePlayer(config.controllingPlayer);
            if (this._checkCancel())
                return;
            await worldState.fetch();
            delete this.characterHistories[charName];
            // Fix 3: clean up histories and lastActionResult for dead/removed characters
            const aliveNames = new Set(Object.keys(worldState.data?.players || {}));
            for (const name of Object.keys(this.characterHistories)) {
                if (!aliveNames.has(name))
                    delete this.characterHistories[name];
            }
            for (const name of Object.keys(agentConfig.lastActionResult)) {
                if (!aliveNames.has(name))
                    delete agentConfig.lastActionResult[name];
            }
            history = this.getHistory(charName);
            if (worldState.data?.scenario_ended) {
                events.log("🏁 Scenario ended via trigger.", "system-msg");
                if (worldState.data?._restart_requested) {
                    events.log("🔄 Restarting scenario...", "system-msg");
                    await agentApi.resetWorld();
                    await worldState.fetch();
                    events.log("✅ Scenario restarted.", "system-msg");
                    VW?.ui?.renderAll?.(worldState.data);
                }
                else {
                    this.stop();
                }
                return;
            }
            const state = worldState.data;
            if (!state?.players?.[config.controllingPlayer]) {
                events.log("Char not found.", "error-msg");
                config.running = false;
                VW?.ui?.updateButtons();
                return;
            }
            const player = state.players?.[charName];
            // NPC turns: simple NPCs act via backend tick_turn - surface what
            // they did from the turn_events (or report they did nothing).
            if (player?.simple_npc) {
                config.busy = false;
                VW?.ui?.updateButtons();
                if (config.running && config.turnBased && this.turnQueue.length > 0) {
                    await TurnQueue.advance();
                    if (worldState.data)
                        VW?.ui?.renderAll(worldState.data);
                }
                this._logActorTurnEvents(charName);
                return;
            }
            // The prompt, threat check and action brackets must all describe the
            // room THIS character is in. `state.current_area` is the server's
            // single active-player view, so using it here showed every other
            // agent the active player's room (bug-565: kyrie was told "library"
            // while her own examine resolved against "foyer").
            const currentArea = state.areas[player?.current_area || state.current_area] || null;
            const lastResult = agentConfig.lastActionResult[charName] || '';
            if (window.AgentState.isBusy(charName, lastResult, player)) {
                const busyPlayer = worldState.players?.[charName];
                const act = busyPlayer?.activity;
                const busyAct = act?.type || (busyPlayer?.state && busyPlayer.state !== 'awake' ? busyPlayer.state : 'busy');
                let detail = '';
                if (act && act.duration_ticks != null) {
                    const remaining = Math.max(0, (act.duration_ticks || 0) - (act.elapsed_ticks || 0));
                    detail = ` - ${remaining} tick${remaining === 1 ? '' : 's'} left`;
                }
                else if (act) {
                    detail = " - no set end ('wake' stops it)";
                }
                return this._endTurnEarly(`⏳ ${charName} is ${busyAct}${detail}...`, 'system-msg');
            }
            // Bonus fix: null-check must come BEFORE using player
            if (!player) {
                config.busy = false;
                VW?.ui?.updateButtons();
                return;
            }
            // Unconscious check - skip actions, character cannot think or act
            if (player.state === 'unconscious') {
                const { message: unconsciousMsg } = window.AgentState.markUnconscious(charName, player, worldState.data, worldState);
                if (unconsciousMsg)
                    events.log(unconsciousMsg, 'system-msg');
                return this._endTurnEarly(null);
            }
            // Just woke up from unconsciousness - skip this turn to let Energy stabilize
            const wakeMsg = window.AgentState.clearUnconscious(charName, player);
            if (wakeMsg) {
                events.log(wakeMsg, 'system-msg');
                window.AgentMemory.storeMemory(charName, `You wake up, groggy and disoriented, your Energy restored to ${player.vitals?.Energy || 'some'}%.`, 7, 'thought');
                return this._endTurnEarly(null);
            }
            // Reflection every 5 turns (per-character counter so it works in simultaneous mode too)
            // Fix 10: use per-char turn counter instead of global turnNumber (which is 0 in simultaneous)
            const charTurnCount = (agentConfig.charTurnCounts = agentConfig.charTurnCounts || {})[charName] = ((agentConfig.charTurnCounts || {})[charName] || 0) + 1;
            if (charTurnCount % 5 === 0 && config.reactiveMode) {
                window.AgentMemory.reflect(charName).catch(() => { });
            }
            const roomParts = PromptBuilder.buildRoomContextParts(state, charName, player, currentArea);
            const vitalsNL = PromptBuilder.describeVitals(player, state, charName);
            const emotionNL = PromptBuilder.buildEmotionContext(player);
            const relationshipNL = PromptBuilder.buildRelationshipContext(player, charName);
            const memoryNL = await PromptBuilder.buildMemoryContext(charName, { report: true });
            if (config.reactiveMode) {
                events.logPhase(charName, 'think', 'observing');
                VW?.ui?.setStatus("Thinking...", "info");
                const turnEvents = state.turn_events || [];
                // Threat check before OBSERVE - so the character naturally notices the threat
                const preObserveThreat = window.ThreatDetector.getThreatAlert(charName, player, currentArea, turnEvents);
                const threatNames = preObserveThreat
                    ? (preObserveThreat.match(/⚠️ IMMEDIATE DANGER: ([^.]+)/)?.[1]?.trim() || '')
                    : '';
                const threatObservationNote = threatNames
                    ? `\n⚠️ ${threatNames} - something about this person sets every instinct on edge. The blood, the emptiness in their eyes, the way they move. They are not here to help you.`
                    : '';
                // Observe uses the SAME full room context as decide/react, so the
                // agent always sees items, people, exits, and a WITNESSED section
                // (with fallback).
                let observeParts = Object.assign({}, roomParts, { extraNote: threatObservationNote || '' });
                // Threat-aware replan check - before deciding so the plan is fresh.
                // task-185: shouldReplan now returns a REASON string (task-340
                // crisis label) or null; setPlan records the turn clock.
                const threatAlert = window.ThreatDetector.getThreatAlert(charName, player, currentArea, turnEvents);
                const needsReplanReason = PlanTracker.shouldReplan(charName, this.turnNumber, threatAlert, player?.vitals);
                if (needsReplanReason) {
                    const plan = await window.PlanManager.generate(charName);
                    if (plan && plan.length > 0) {
                        PlanTracker.setPlan(charName, plan, this.turnNumber);
                        events.log(`⚠️ ${charName} replanned - ${needsReplanReason}: ${plan.join(' → ')}`, 'msg-crisis');
                        // task-185: the decide prompt reuses this snapshot - refresh
                        // the plan part so a plan generated THIS turn is visible
                        // THIS turn instead of next turn.
                        observeParts.plan = PromptBuilder.buildPlanContext(charName);
                    }
                }
                if (this._checkCancel())
                    return;
                // ── Multi-action turn (task-352, 2026-10-08) ──
                // A turn holds up to the tier budget (major 1 · minor 1 · free 3).
                // This loops decide→act→react, rebuilding the prompt each pass from
                // fresh state so spent slots hide the verbs the character can no
                // longer afford (room-context feeds turn_slots to the brackets;
                // `wait` is exempt, it is the turn's exit). The budget is a CEILING
                // not a quota: the loop exits on "done" - wait, nothing worth doing,
                // or nothing left affordable - so a character who is fine takes one
                // action and stops, exactly as before. Hard cap = the budget total.
                const MAX_ACTIONS_PER_TURN = 5;
                let actionStep = 0;
                let loopLastResult = lastResult;
                let turnDone = false;
                while (!turnDone && actionStep < MAX_ACTIONS_PER_TURN) {
                    actionStep += 1;
                    // The player object the prompt is built from must be the same
                    // one the bracket-filter reads: otherwise the "ACTIONS LEFT"
                    // section would show the stale budget while the brackets show
                    // the fresh, reduced one.
                    let promptPlayer = player;
                    if (actionStep > 1) {
                        // Re-read the world: the previous action moved/spent slots and
                        // may have revealed items, so rebuild the room context. Vitals,
                        // emotion and memory stay at their turn-start values.
                        // Fix 7: wait for any in-flight fetch to complete (coalesce)
                        if (worldState._inflight)
                            await worldState._inflight;
                        await worldState.fetch();
                        const loopState = worldState.data || state;
                        const loopPlayer = loopState?.players?.[charName] || player;
                        promptPlayer = loopPlayer;
                        const loopArea = loopState?.areas?.[loopPlayer?.current_area || loopState.current_area] || currentArea;
                        const loopRoomParts = PromptBuilder.buildRoomContextParts(loopState, charName, loopPlayer, loopArea);
                        observeParts = Object.assign({}, loopRoomParts, { plan: PromptBuilder.buildPlanContext(charName) });
                        if (this._checkCancel())
                            return;
                    }
                    // CONVERSATION-STYLE LOOP: think + decide in ONE call, and the
                    // prompt + response are pushed into the per-character history
                    // ([system, user, assistant, ...]) so the agent remembers its own
                    // earlier words across phases and turns - no more self-contradiction
                    // between decide and react (e.g. changing a favorite color).
                    const thinkDecidePrompt = PromptBuilder.buildReactionPrompt(promptPlayer, observeParts, vitalsNL, emotionNL, relationshipNL, memoryNL, loopLastResult, false, true);
                    const combinedPrompt = threatAlert ? threatAlert + '\n\n' + thinkDecidePrompt : thinkDecidePrompt;
                    // Fix #6: each decide is a fresh system + user call; previous
                    // assistant outputs are not replayed as active context.
                    const decideHistory = [
                        history[0], // system prompt (persistent rules)
                        { role: 'user', content: combinedPrompt }
                    ];
                    const combinedResponse = await this._callLLMMessages(decideHistory, 'think-decide', charName);
                    // Do NOT replay the assistant output into persistent history.
                    // The react phase uses its own fresh messages; the next turn
                    // restarts with a clean [system, user] context.
                    if (combinedResponse === null) {
                        events.log(`❌ LLM call failed for ${charName} (think/decide phase) - stopping agent`, 'error-msg');
                        VW?.ui?.setStatus("LLM Error - Stopped", "error");
                        config.running = false;
                        return;
                    }
                    events.logPhase(charName, 'decide', 'deciding');
                    VW?.ui?.setStatus("Deciding...", "info");
                    let parsedDecide = ResponseParser.parseReaction(combinedResponse) ?? { inner: '', speech: null, speechVolume: 'say', action: '', emote: null, memory: null, emotion: null, parseError: null };
                    if (parsedDecide.parseError)
                        parsedDecide = await this._retryOnceOnParseError(charName, decideHistory, 'think-decide', ResponseParser.parseReaction, parsedDecide);
                    if (parsedDecide.parseError) {
                        events.logParseError(charName, 'think-decide', parsedDecide.parseError, combinedResponse);
                    }
                    let { inner, speech: decisionSpeech, speechVolume, action: finalAction, emote: decisionEmote, target: decisionTarget } = parsedDecide;
                    this._applyFeltEmotion(charName, parsedDecide.emotion);
                    this._learnNames(charName, parsedDecide.learnedNames);
                    if (inner) {
                        events.logThought(charName, inner);
                    }
                    events.trackAction(charName, inner, null, '', '');
                    if (!agentConfig.lastRoom[charName] && player.current_area)
                        agentConfig.lastRoom[charName] = player.current_area;
                    let actionRejected = '';
                    let actionRejectCategory = '';
                    if (finalAction) {
                        const verdict = ActionNormalizer.classifyAction(finalAction, charName);
                        if (!verdict.ok) {
                            // The category is part of the message on purpose: a
                            // malformed payload and an unknown verb are ENGINE
                            // failures, and a reader (or a filter) must be able to
                            // tell them apart from a world refusal.
                            events.log(`⚠️ ${charName} invalid action: "${finalAction}" - skipping [${verdict.category}: ${verdict.detail}]`, 'error-msg');
                            actionRejected = finalAction;
                            actionRejectCategory = verdict.category;
                            finalAction = '';
                        }
                    }
                    else if (parsedDecide.parseError && /schema_invalid/.test(parsedDecide.parseError)) {
                        // The model DID choose an action, but the engine could not
                        // read the payload. The command never reached the world -
                        // say exactly that instead of faking a world refusal.
                        actionRejected = '(unreadable command)';
                        actionRejectCategory = 'schema_invalid';
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
                        actionResult = this._surfaceRejectedAction(charName, actionRejected, actionRejectCategory);
                        actionSucceeded = false;
                        events.log(actionResult, 'msg-result', { outcome: 'failure' }, charName);
                    }
                    if (finalAction) {
                        events.logPhase(charName, 'act', finalAction);
                        const noopAction = this._isNoopAction(finalAction);
                        if (!finalAction.startsWith('speak ') && !noopAction)
                            events.log(`[Action] ${finalAction}`, "msg-action");
                        if (this._checkCancel())
                            return;
                        if (noopAction) {
                            actionResult = 'You stand still and wait, watching and listening.';
                            actionSucceeded = true;
                            events.log(actionResult, 'msg-result', { outcome: 'minor' }, charName);
                        }
                        else
                            try {
                                const data = await agentApi.action(finalAction, charName, { enforceSlots: true });
                                if (data?.scenario_ended) {
                                    events.log("🏁 Scenario ended via trigger.", "system-msg");
                                    if (data?._restart_requested) {
                                        events.log("🔄 Restarting scenario...", "system-msg");
                                        await agentApi.resetWorld();
                                        await worldState.fetch();
                                        delete this.characterHistories[charName];
                                        history = this.getHistory(charName);
                                        events.log("✅ Scenario restarted.", "system-msg");
                                        VW?.ui?.renderAll?.(worldState.data);
                                    }
                                    else {
                                        this.stop();
                                    }
                                    return;
                                }
                                actionResult = data?.output || '';
                                actionSucceeded = data?.success !== false;
                                PlanTracker.trackStep(charName, finalAction, actionResult, actionSucceeded);
                                let outputText = actionResult;
                                if (data?.system_messages) {
                                    data.system_messages.forEach((systemMessage) => events.log(systemMessage, 'system-msg'));
                                }
                                const narrationUi = agentNarrationUI();
                                const narrationMode = narrationUi?.getMode();
                                let narratedText = null;
                                if (narrationMode === 'ai' && config.apiKey && config.model) {
                                    // Non-null assertion matches the original bare call:
                                    // getMode() only returns 'ai' when the module loaded.
                                    narratedText = await narrationUi.getNarratedActionResult(outputText, charName, finalAction);
                                    if (narratedText)
                                        outputText = narratedText;
                                }
                                agentConfig.lastActionResult[charName] = outputText;
                                // task-340: results are first-class rows - outcome-tinted,
                                // never card-breaking; AI-narrated substitutions are marked.
                                if (!outputText.includes('says:')) {
                                    if (narratedText)
                                        events.log(outputText, 'msg-narrated');
                                    else if (outputText.includes('ValueError'))
                                        events.log(outputText, 'error-msg');
                                    else
                                        events.log(outputText, 'msg-result', { outcome: actionSucceeded ? 'success' : 'failure' }, charName);
                                }
                                events.trackAction(charName, '', null, finalAction, outputText);
                                const area = worldState.players?.[charName]?.current_area;
                                if (area)
                                    agentConfig.lastRoom[charName] = area;
                                worldState.fetch();
                            }
                            catch (err) {
                                const m = err instanceof Error ? err.message : String(err);
                                events.log(`Action error: ${m}`, 'error-msg');
                                actionResult = `Error: ${m}`;
                            }
                    }
                    // ── Budget-exhaustion auto-retry: if server rejected for
                    // "no major action left", immediately substitute "wait" instead
                    // of asking the LLM (which would likely pick another major action).
                    const budgetExhausted = !actionSucceeded && /no major action left|major action budget exhausted/i.test(actionResult);
                    if (budgetExhausted) {
                        events.log(`↩️ ${charName}: budget exhausted — auto-substituting "wait"`, 'system-msg');
                        actionResult = 'You wait, watching and listening.';
                        actionSucceeded = true;
                        PlanTracker.trackStep(charName, 'wait', actionResult, true);
                    }
                    else if (!actionSucceeded && config.autoRetryInvalid && actionResult) {
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
                            agentConfig.lastActionResult[charName] = actionResult;
                        }
                        else if (!isNowResting) {
                            // Fix 7: coalesce with any in-flight fetch
                            if (worldState._inflight)
                                await worldState._inflight;
                            await worldState.fetch();
                            const freshState = worldState.data;
                            const freshPlayer = freshState?.players?.[charName] || player;
                            const freshRoom = freshState?.areas?.[freshPlayer?.current_area || freshState.current_area] || currentArea;
                            events.logPhase(charName, 'react', 'reacting');
                            VW?.ui?.setStatus("Reacting...", "info");
                            const movedViaDash = finalAction.split(/\s+/)[0].toLowerCase() === 'dash';
                            const tickNum = worldState.data?.time_ticks ?? 0;
                            const areaName = freshRoom?.name || freshPlayer?.current_area || freshState?.current_area || '';
                            // task-185: currentArea is the turn-start (pre-action) room -
                            // if it differs from the fresh room the character MOVED this
                            // action, and "surroundings are unchanged" was lying while
                            // pointing the model at a stale observation of the old room.
                            const areaBefore = currentArea?.name || player?.current_area || '';
                            const areaChanged = !movedViaDash && !!areaName && areaName !== areaBefore;
                            const reactContext = movedViaDash
                                ? `[Tick ${tickNum}] You just sprinted and are now in ${areaName} - react to arriving here.`
                                : areaChanged
                                    ? `[Tick ${tickNum}] You just moved - you are now in ${areaName}. The full description of your new surroundings is in === WHAT HAPPENED === below.`
                                    : `[Tick ${tickNum}] You are still in ${areaName}. Your surroundings are unchanged.`;
                            const reactPrompt = PromptBuilder.buildResultReactionPrompt(charName, freshPlayer, reactContext, vitalsNL, emotionNL, relationshipNL, inner, finalAction || '', actionResult, memoryNL, decisionSpeech);
                            // task-XXX: dedicated minimal react call. The react phase cannot
                            // act, so replaying the full decide exchange (~2-3k of persona/
                            // room/plan/available-actions) plus the action-law system was
                            // pure weight - and the cached system even said "Emit ONE action"
                            // while the react user message said the opposite. Fresh 2-message
                            // conversation instead: react-specific system + ONE user message;
                            // WHAT HAPPENED carries the outcome. The exchange is still
                            // mirrored into `history` below for future-turn continuity.
                            const reactMessages = [
                                { role: 'system', content: PromptBuilder.buildReactSystemPrompt(charName, freshPlayer) },
                                { role: 'user', content: reactPrompt },
                            ];
                            let reactResponse = await this._callLLMMessages(reactMessages, 'result-reaction', charName);
                            if (reactResponse === null) {
                                events.log(`❌ LLM call failed for ${charName} (reaction phase) - stopping agent`, 'error-msg');
                                VW?.ui?.setStatus("LLM Error - Stopped", "error");
                                config.running = false;
                                return;
                            }
                            let parsedReact = ResponseParser.parseResultReaction(reactResponse) ?? { inner: '', speech: null, speechVolume: 'say', emote: null, memory: null, emotion: null, parseError: null };
                            if (parsedReact.parseError && reactResponse) {
                                // one same-conversation retry (repaired/truncated JSON):
                                // show the broken reply, ask for a complete one.
                                events.log(`⚠️ ${charName}: result-reaction response was repaired (truncated JSON) - retrying once.`, 'error-msg');
                                const retryMessages = [
                                    reactMessages[0],
                                    reactMessages[1],
                                    { role: 'assistant', content: reactResponse || '' },
                                    { role: 'user', content: 'Your previous reply was cut off mid-JSON. Respond again with COMPLETE raw JSON - same schema, and finish every field you start.' },
                                ];
                                const retried = await this._callLLMMessages(retryMessages, 'result-reaction', charName);
                                if (retried) {
                                    reactResponse = retried;
                                    parsedReact = ResponseParser.parseResultReaction(reactResponse) ?? parsedReact;
                                }
                            }
                            if (parsedReact.parseError) {
                                events.logParseError(charName, 'result-reaction', parsedReact.parseError, reactResponse);
                            }
                            history.push({ role: 'user', content: reactPrompt });
                            history.push({ role: 'assistant', content: reactResponse || '' });
                            if (!reactResponse || !String(reactResponse).trim()) {
                                events.log(`⚠️ ${charName}: result-reaction returned empty - skipping react`, 'error-msg');
                            }
                            const { inner: reactionInner, speech: reactionSpeech, speechVolume: reactionVolume, emote: reactionEmote, memory: reactionMemory } = parsedReact;
                            if (reactionInner) {
                                events.logThought(charName, reactionInner);
                            }
                            this._applyFeltEmotion(charName, parsedReact.emotion);
                            this._learnNames(charName, parsedReact.learnedNames);
                            if (reactionSpeech) {
                                await this._speakLine(charName, player, reactionSpeech, reactionVolume);
                            }
                            if (reactionEmote) {
                                await this._performEmote(charName, reactionEmote);
                            }
                            this._storeReactionMemory(charName, reactionMemory, parsedReact.emotion, actionSucceeded, actionResult);
                            events.trackAction(charName, reactionInner, reactionSpeech, null, '');
                        }
                        else {
                            events.trackAction(charName, '', null, finalAction, actionResult);
                        }
                    }
                    // ── Continue or end the multi-action turn (task-352) ──
                    loopLastResult = actionResult || loopLastResult;
                    const choseNothing = !finalAction || this._isNoopAction(finalAction);
                    if (choseNothing) {
                        turnDone = true;
                    }
                    else {
                        // Exit when the remaining budget can pay for nothing at all.
                        // Any positive slot still buys at least a look, so the next
                        // prompt (which already hides what is unaffordable) is the
                        // real gate; this is only the "budget is empty" stop.
                        const slotsNow = (worldState.data?.players?.[charName]?.turn_slots);
                        // bug-544: an empty `{}` is "no budget published" (the
                        // engine lazily fills it), not "budget empty" - only a
                        // published-and-spent budget ends the turn, otherwise a
                        // fresh character's loop exited before acting once.
                        const spentOut = !!slotsNow && Object.keys(slotsNow).length > 0
                            && !Object.values(slotsNow).some((n) => n > 0);
                        if (spentOut)
                            turnDone = true;
                    }
                }
            }
            else {
                // ── Non-reactive (combined) mode ──
                VW?.ui?.setStatus("Thinking...", "info");
                const reactionPrompt = PromptBuilder.buildReactionPrompt(player, roomParts, vitalsNL, emotionNL, relationshipNL, memoryNL, lastResult, true);
                // Fix #6: combined mode also uses fresh context, not accumulated history.
                const combinedHistory = [
                    history[0],
                    { role: 'user', content: reactionPrompt }
                ];
                const reactionResponse = await this._callLLMMessages(combinedHistory, 'combined', charName);
                if (reactionResponse === null) {
                    events.log(`❌ LLM call failed for ${charName} - stopping agent`, 'error-msg');
                    VW?.ui?.setStatus("LLM Error - Stopped", "error");
                    config.running = false;
                    return;
                }
                const parsedNonReactive = ResponseParser.parseReaction(reactionResponse) ?? { inner: '', speech: null, speechVolume: 'say', action: '', emote: null, memory: null, emotion: null, parseError: null };
                if (parsedNonReactive.parseError) {
                    events.logParseError(charName, 'combined', parsedNonReactive.parseError, reactionResponse);
                }
                let { inner, speech, speechVolume, action, emote: reactionEmote, memory: reactionMemory, target: speechTarget } = parsedNonReactive;
                if (inner) {
                    events.log(`[${player.name} inner] ${inner}`, "msg-thought");
                }
                this._applyFeltEmotion(charName, parsedNonReactive.emotion);
                this._learnNames(charName, parsedNonReactive.learnedNames);
                if (speech) {
                    await this._speakLine(charName, player, speech, speechVolume, speechTarget);
                }
                this._storeReactionMemory(charName, reactionMemory, parsedNonReactive.emotion);
                events.trackAction(charName, inner, speech, null, '');
                if (!agentConfig.lastRoom[charName] && player.current_area)
                    agentConfig.lastRoom[charName] = player.current_area;
                let finalAction = action;
                // The non-reactive path validates the command too. Without
                // this, a malformed payload went straight to /api/action and
                // a stringified object reached the world as a command.
                let combinedRejected = '';
                let combinedRejectCategory = '';
                if (finalAction) {
                    const verdict = ActionNormalizer.classifyAction(finalAction, charName);
                    if (!verdict.ok) {
                        events.log(`⚠️ ${charName} invalid action: "${finalAction}" - skipping [${verdict.category}: ${verdict.detail}]`, 'error-msg');
                        combinedRejected = finalAction;
                        combinedRejectCategory = verdict.category;
                        finalAction = '';
                    }
                }
                else if (parsedNonReactive.parseError && /schema_invalid/.test(parsedNonReactive.parseError)) {
                    combinedRejected = '(unreadable command)';
                    combinedRejectCategory = 'schema_invalid';
                }
                const noopAction = this._isNoopAction(finalAction);
                if (finalAction && !finalAction.startsWith('speak ') && !noopAction)
                    events.log(`[Action] ${finalAction}`, "msg-action");
                if (finalAction && noopAction) {
                    agentConfig.lastActionResult[charName] = 'You stand still and wait, watching and listening.';
                    events.trackAction(charName, inner, speech, 'wait', 'waits.');
                }
                else if (finalAction) {
                    try {
                        const data = await agentApi.action(finalAction, charName, { enforceSlots: true });
                        const output = data?.output || data?.error || '';
                        if (data?.system_messages) {
                            data.system_messages.forEach((systemMessage) => events.log(systemMessage, 'system-msg'));
                        }
                        agentConfig.lastActionResult[charName] = output;
                        if (output && !output.includes('says:'))
                            events.log(output, output.includes('ValueError') ? 'error-msg' : 'system-msg');
                        events.trackAction(charName, '', null, finalAction, output);
                        const area = worldState.players?.[charName]?.current_area;
                        if (area)
                            agentConfig.lastRoom[charName] = area;
                        // Fix 7: coalesce with any in-flight fetch
                        if (worldState._inflight)
                            await worldState._inflight;
                        await worldState.fetch();
                        if (reactionEmote && data?.success !== false) {
                            await this._performEmote(charName, reactionEmote);
                        }
                    }
                    catch (err) {
                        events.log(`Action error: ${err instanceof Error ? err.message : String(err)}`, 'error-msg');
                        // Fix 7: coalesce with any in-flight fetch
                        if (worldState._inflight)
                            await worldState._inflight;
                        await worldState.fetch();
                    }
                }
                else if (combinedRejected) {
                    const rejectionText = this._surfaceRejectedAction(charName, combinedRejected, combinedRejectCategory);
                    events.log(rejectionText, 'msg-result', { outcome: 'failure' }, charName);
                }
            }
            if (config.running && config.turnBased && this.turnQueue.length > 0) {
                await TurnQueue.advance();
                if (worldState.data)
                    VW?.ui?.renderAll(worldState.data);
            }
            // Fix #6: reset persistent history to system-only after each turn.
            const turnHistory = this.getHistory(charName);
            const sysOnly = turnHistory.length > 0 ? [turnHistory[0]] : [];
            this.characterHistories[charName] = sysOnly;
        }
        finally {
            worldState.setRuntimeFocusForCharacter(config.controllingPlayer || charName);
            config.busy = false;
            VW?.ui?.updateButtons();
            VW?.ui?.syncRateLimitDisplay();
            VW?.ui?.setStatus(config.running ? "Waiting..." : "Idle.", "info");
        }
    }
    async stepOnce() {
        // A4: a stop/cancel from a PREVIOUS run must not ghost into this one
        // ("Step cancelled." firing on a fresh ⏭ was the stale flag leaking).
        this._cancelRequested = false;
        this._paused = false;
        this._pausedAt = null;
        this._resumeAfterVisibility = false;
        agentConfig.stepsRun = 0;
        if (config.busy || config.running) {
            events.log("Already running.", "system-msg");
            return;
        }
        if (config.turnBased && this.turnQueue.length === 0)
            TurnQueue.initialize();
        // Fix 8: use centralized resolution
        config.controllingPlayer = this._resolveControllingPlayer();
        const steppedCharacter = config.controllingPlayer;
        worldState.setRuntimeFocusForCharacter(steppedCharacter);
        try {
            await this.step();
            if (config.turnBased && this.turnQueue.length > 0) {
                await TurnQueue.advance();
                config.controllingPlayer = TurnQueue.getCurrentCharacter();
                worldState.setRuntimeFocusForCharacter(config.controllingPlayer);
                if (worldState.data)
                    VW?.ui?.renderAll(worldState.data);
            }
            else if (!config.turnBased && config.controllingPlayer) {
                // No turn-based mode: the stepped character's turn is one full
                // turn - end it so the clock advances and new-turn effects run
                // (behave like turn-based with a single-character queue).
                await TurnQueue.endTurn();
                this._logActorTurnEvents(config.controllingPlayer);
                if (worldState.data)
                    VW?.ui?.renderAll(worldState.data);
            }
        }
        finally {
            worldState.setRuntimeFocusForCharacter(config.controllingPlayer || steppedCharacter);
            config.busy = false;
            VW?.ui?.updateButtons();
            VW?.ui?.setStatus(config.running ? "Waiting..." : "Idle.", "info");
        }
    }
    async start() {
        // The toolbar's Play button resumes a paused run without rebuilding its
        // queue, resetting its step count, or discarding async deadlines.
        if (config.running) {
            if (this._paused)
                this.resume();
            return;
        }
        if (config.turnBased) {
            this.characterHistories = {};
            if (this.turnQueue.length === 0) {
                TurnQueue.initialize();
            }
            if (this.turnQueue.length === 0) {
                events.log("No characters.", "error-msg");
                return;
            }
            config.controllingPlayer = this.turnQueue[this.currentTurnIndex] || this.turnQueue[0];
        }
        else {
            // Fix 8: use centralized resolution
            config.controllingPlayer = this._resolveControllingPlayer();
            if (!config.controllingPlayer) {
                events.log("No character selected.", "error-msg");
                return;
            }
        }
        agentConfig.stepsRun = 0;
        const maxInput = document.getElementById('sim-max-steps');
        agentConfig.maxSteps = maxInput ? parseInt(maxInput.value) || 0 : 0;
        config.running = true;
        VW?.ui?.updateButtons();
        VW?.ui?.setStatus("Running...", "info");
        VW?.ui?.showPlayPause(false, true);
        VW?.ui?.updateMaxStepsDisplay();
        // A4: a stop/cancel from a PREVIOUS run must not ghost into this one
        // ("Step cancelled." firing on a fresh ▶ was the stale flag leaking).
        this._cancelRequested = false;
        (async () => {
            while (config.running) {
                if (this._paused) {
                    await new Promise(resolve => setTimeout(resolve, 250));
                    continue;
                }
                let didAct = true;
                if (window.VWSimultaneous.isRoomMode(config.simultaneousMode)) {
                    await this._simultaneousRoomStep();
                }
                else if (config.simultaneousMode === 'simultaneous') {
                    didAct = await this._simultaneousStep();
                }
                else if (config.simultaneousMode) {
                    await this._simultaneousStep();
                }
                else {
                    await this.step();
                }
                if (this._paused)
                    continue;
                // Async mode counts completed character turns, not idle scheduler
                // polls. A 5–120 second cooldown must not hit the max-step limit
                // after a handful of 250 ms checks.
                if (!didAct) {
                    await new Promise(resolve => setTimeout(resolve, 250));
                    continue;
                }
                if (this._cancelRequested) {
                    this.cancel();
                    break;
                }
                if (!config.turnBased && config.controllingPlayer && !config.simultaneousMode) {
                    await TurnQueue.endTurn();
                    this._logActorTurnEvents(config.controllingPlayer);
                    if (worldState.data)
                        VW?.ui?.renderAll(worldState.data);
                }
                agentConfig.stepsRun++;
                const turnsRun = config.turnBased ? Math.floor(agentConfig.stepsRun / Math.max(1, this.turnQueue.length)) : agentConfig.stepsRun;
                VW?.ui?.updateMaxStepsDisplay();
                if (agentConfig.maxSteps > 0 && turnsRun >= agentConfig.maxSteps) {
                    this.stop(`⏹️ Run complete - ${agentConfig.maxSteps} turns done. Press ▶ to continue.`);
                    break;
                }
                await new Promise(resolve => setTimeout(resolve, config.simultaneousMode === 'simultaneous' ? 250 : (config.simultaneousMode ? 800 : 2000)));
            }
        })();
    }
    /**
     * task-101 "simultaneous": every autonomous character has its own act
     * countdown. Each loop iteration decrements all countdowns; the first
     * character ready processes its full turn through the normal per-character
     * pipeline, then its countdown restarts.
     *
     * The human is never *auto-acted*, but they are a participant in the round
     * (task-533): once every autonomous character has taken their turn, the
     * human is prompted at their own cadence. That ordering is the point - the
     * human is the one the round is waiting on, so they are asked last. They can
     * also pass with the "End round" control, which resolves them without acting
     * so a round can never hang on an idle player.
     */
    async _simultaneousStep() {
        if (!worldState.data)
            await worldState.fetch();
        const players = worldState.data?.players || {};
        const names = Object.keys(players);
        const now = Date.now();
        const alive = (name) => {
            const p = players[name];
            return p && (p.state !== 'dead' || config.ghostMode);
        };
        const participants = names.filter(alive);
        for (const name of Object.keys(this._simDeadlines)) {
            if (!participants.includes(name))
                delete this._simDeadlines[name];
        }
        for (const name of names) {
            if (alive(name) && this._simDeadlines[name] === undefined) {
                this._simDeadlines[name] = now + window.VWSimultaneous.jitteredCooldownMs(config.getTalkativeness(name));
            }
        }
        // The world state and action endpoint are shared, so dispatch one turn
        // at a time. If several deadlines elapsed during a long turn, the
        // earliest arrival runs first; equal deadlines retain roster order.
        const charName = window.VWSimultaneous.firstReadyCharacter(participants, this._simDeadlines, now);
        if (charName === null)
            return false;
        this._simDeadlines[charName] = now + window.VWSimultaneous.jitteredCooldownMs(config.getTalkativeness(charName));
        const prevControlling = config.controllingPlayer;
        config.controllingPlayer = charName;
        try {
            if (events.isAutonomous(charName))
                await this.step();
            else
                await this._humanTurn(charName);
        }
        finally {
            config.controllingPlayer = prevControlling;
            worldState.setRuntimeFocusForCharacter(prevControlling);
        }
        this.markSimResolved(charName);
        await this._closeSimRoundIfComplete();
        return true;
    }
    /** Reset one character's scheduled arrival after a pace edit. */
    resetSimCharacterDeadline(charName) {
        if (!charName || !config.running || !config.simultaneousMode || !worldState.data?.players?.[charName])
            return;
        this._simDeadlines[charName] = Date.now() + window.VWSimultaneous.jitteredCooldownMs(config.getTalkativeness(charName));
    }
    resetSimDeadlines() {
        this._simDeadlines = {};
    }
    /** Pause at the current turn boundary and preserve real-time cooldowns. */
    pause(reason = 'Paused.') {
        if (!config.running || this._paused)
            return;
        this._paused = true;
        this._pausedAt = Date.now();
        VW?.ui?.showPlayPause(true, false);
        VW?.ui?.updateButtons();
        VW?.ui?.setStatus(reason, 'info');
    }
    resume() {
        if (!config.running || !this._paused)
            return;
        const pausedFor = this._pausedAt === null ? 0 : Math.max(0, Date.now() - this._pausedAt);
        for (const name of Object.keys(this._simDeadlines))
            this._simDeadlines[name] += pausedFor;
        this._pausedAt = null;
        this._paused = false;
        VW?.ui?.showPlayPause(false, true);
        VW?.ui?.updateButtons();
        VW?.ui?.setStatus('Running...', 'info');
    }
    /** Auto-pause only a run that was active before the tab was hidden. */
    setVisibilityPaused(hidden) {
        if (hidden) {
            this._resumeAfterVisibility = !!config.running && !this._paused;
            if (this._resumeAfterVisibility)
                this.pause('Tab unfocused - paused.');
            return;
        }
        const shouldResume = this._resumeAfterVisibility;
        this._resumeAfterVisibility = false;
        if (shouldResume)
            this.resume();
    }
    /**
     * task-101 "simultaneous per room": rooms resolve independently while
     * characters inside a room still act in order. Each iteration decrements
     * every room countdown; the first ready room runs its (autonomous, living)
     * characters sequentially, then the room's countdown restarts. A room's
     * cadence is its fastest member's.
     */
    async _simultaneousRoomStep() {
        if (!worldState.data)
            await worldState.fetch();
        const players = worldState.data?.players || {};
        const rooms = window.VWSimultaneous.groupByRoom(players, {
            isAutonomous: (name) => events.isAutonomous(name),
            ghostMode: config.ghostMode,
        });
        for (const area of Object.keys(rooms)) {
            if (this._simRoomCountdowns[area] === undefined) {
                this._simRoomCountdowns[area] = window.VWSimultaneous.roomCooldown(rooms[area], players);
            }
        }
        window.VWSimultaneous.tickCountdowns(this._simRoomCountdowns);
        const area = window.VWSimultaneous.firstReadyRoom(rooms, this._simRoomCountdowns);
        if (area === null) {
            // No room ready. The human is still a round participant (task-533),
            // so once every room has gone they get prompted at their own cadence.
            if (this._simRoundComplete())
                return;
            const human = Object.keys(players).find(name => !events.isAutonomous(name)
                && (players[name]?.state !== 'dead' || config.ghostMode)
                && this._simCountdowns[name] <= 0);
            if (!human)
                return;
            this._simCountdowns[human] = window.VWSimultaneous.cooldownFor(players[human]);
            const prevHuman = config.controllingPlayer;
            config.controllingPlayer = human;
            try {
                await this._humanTurn(human);
            }
            finally {
                config.controllingPlayer = prevHuman;
                worldState.setRuntimeFocusForCharacter(prevHuman);
            }
            this.markSimResolved(human);
            await this._closeSimRoundIfComplete();
            return;
        }
        const order = rooms[area];
        this._simRoomCountdowns[area] = window.VWSimultaneous.roomCooldown(order, players);
        const prevControlling = config.controllingPlayer;
        try {
            for (const charName of order) {
                if (this._cancelRequested || !config.running)
                    break;
                config.controllingPlayer = charName;
                await this.step();
                this.markSimResolved(charName);
            }
        }
        finally {
            config.controllingPlayer = prevControlling;
            worldState.setRuntimeFocusForCharacter(prevControlling);
        }
        await this._closeSimRoundIfComplete();
    }
    /**
     * Record that *name* has taken their turn in the current simultaneous round.
     * @param {string} name
     */
    markSimResolved(name) {
        if (!name)
            return;
        if (!this._simRound)
            this._simRound = new Set();
        window.VWSimRound.markResolved(this._simRound, name);
    }
    /**
     * Everyone whose turn counts toward a round: every living character, human
     * included. The human is a participant, not an exemption - a slow player
     * stalls the world, which is the same contract turn-based mode already has.
     * @returns {string[]}
     */
    _simParticipants() {
        return window.VWSimRound.participants(worldState.data?.players || {}, {
            ghostMode: config.ghostMode
        });
    }
    /** True when every participant has taken their turn this round. */
    _simRoundComplete() {
        return window.VWSimRound.isComplete(this._simParticipants(), this._simRound);
    }
    /**
     * Close the round if everyone has gone: run the world turn pipeline and
     * start a fresh round.
     *
     * This is the whole of task-533. Simultaneous mode used to step characters
     * but never call `endTurn()`, so `tick_turn()` never ran: no vitals decay, no
     * background simulation, no soak orders, no item ticks, no time triggers,
     * and a frozen clock. Nothing in the world happened at all.
     */
    async _closeSimRoundIfComplete() {
        if (!this._simRoundComplete())
            return false;
        this._simRound = new Set();
        await TurnQueue.endTurn();
        if (worldState.data)
            VW?.ui?.renderAll(worldState.data);
        return true;
    }
    /**
     * The "End round" control: resolve every human participant without acting,
     * so a round can never hang on an idle player.
     *
     * Deliberately no timeout. The world advances only because the player said
     * so - it does not quietly run on while someone is reading. Autonomics are
     * not touched; only the human's own turn is surrendered, and only if they
     * have not already taken it.
     */
    async endSimRound() {
        const human = this._simParticipants().find(name => !events.isAutonomous(name));
        if (!human)
            return false;
        if (!(this._simRound || new Set()).has(human)) {
            events.log(`⏭️ ${human} passes - round closed.`, 'system-msg');
            this.markSimResolved(human);
        }
        return this._closeSimRoundIfComplete();
    }
    stop(reason = 'Agent stopped.') {
        this._paused = false;
        this._pausedAt = null;
        this._resumeAfterVisibility = false;
        // Fix 4: clear simultaneous mode deadlines/countdowns so they don't poison next run
        this._simDeadlines = {};
        this._simCountdowns = {};
        this._simRoomCountdowns = {};
        this._simRound = new Set();
        config.running = false;
        VW?.ui?.updateButtons();
        events.log(reason, 'system-msg');
        VW?.ui?.setStatus("Idle.", "info");
        VW?.ui?.showPlayPause(true, false);
        VW?.ui?.updateMaxStepsDisplay();
    }
    reset() {
        this.stop();
        PlanTracker.resetAll();
        this.characterHistories = {};
        agentConfig.lastActionResult = {};
        agentConfig.lastRoom = {};
        this.turnQueue = [];
        this.currentTurnIndex = 0;
        this.turnNumber = 0;
        this.initiativeRolls = {};
        this._simCountdowns = {};
        this._simRoomCountdowns = {};
        this._simDeadlines = {};
        this._paused = false;
        this._pausedAt = null;
        this._resumeAfterVisibility = false;
    }
    nudge(charName, text) {
        if (!text || !charName)
            return;
        this.getHistory(charName).push({ role: 'user', content: `[Sensory event] ${text}` });
        events.log(`[Nudge -> ${charName}] ${text}`, 'system-msg');
    }
    /**
     * Give the agent feedback when its chosen action is rejected, instead of
     * silently dropping it. The rejection lands in lastActionResult (so DECIDE
     * sees it next turn) - no memory write: the hint is transient system
     * feedback, not something the character remembers.
     *
     * The wording is CATEGORY-SENSITIVE on purpose. A malformed command or an
     * unknown verb is an engine-side refusal, and saying "you try to X, but
     * you can't do that" made characters invent supernatural barriers to
     * explain a malformed JSON payload. The character is told what actually
     * happened: the command never reached the world.
     *
     * @param {string} charName - Character name
     * @param {string} rejectedAction - The rejected action text
     * @param {string} category - 'schema_invalid' | 'unknown_verb' | 'empty'
     */
    _surfaceRejectedAction(charName, rejectedAction, category = 'unknown_verb') {
        const text = ActionNormalizer.rejectionText(category, rejectedAction);
        agentConfig.lastActionResult[charName] = text;
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
        if (!failedResult || /while unconscious/i.test(failedResult))
            return null;
        events.log(`↩️ ${charName}: auto-retry after failed action "${attempted}"`, 'system-msg');
        events.logPhase(charName, 'decide', 'auto-retry');
        VW?.ui?.setStatus?.('Retrying...', 'info');
        const prompt = PromptBuilder.buildRetryPrompt(attempted, failedResult);
        history.push({ role: 'user', content: prompt });
        const response = await this._callLLMMessages(history, 'auto-retry', charName);
        if (response === null) {
            history.pop(); // LLM call failed - drop the retry prompt, keep history as before
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
            events.log(`⚠️ ${charName} retry chose an invalid action: "${retryAction || '(none)'}" - giving up`, 'error-msg');
            return null;
        }
        events.logPhase(charName, 'act', retryAction);
        events.log(`[Action] ${retryAction}`, 'msg-action');
        try {
            const data = await agentApi.action(retryAction, charName, { enforceSlots: true });
            if (data?.scenario_ended) {
                events.log('🏁 Scenario ended via trigger.', 'system-msg');
                if (data?._restart_requested) {
                    events.log('🔄 Restarting scenario...', 'system-msg');
                    await agentApi.resetWorld();
                    await worldState.fetch();
                    events.log('✅ Scenario restarted.', 'system-msg');
                }
                else {
                    this.stop();
                }
                return null;
            }
            const result = data?.output || '';
            const succeeded = data?.success !== false;
            agentConfig.lastActionResult[charName] = result;
            PlanTracker.trackStep(charName, retryAction, result, succeeded);
            events.trackAction(charName, '', null, retryAction, result);
            if (result && !result.includes('says:')) {
                events.log(result, result.includes('ValueError') ? 'error-msg' : 'msg-result', { outcome: succeeded ? 'success' : 'failure' }, charName);
            }
            return { finalAction: retryAction, actionResult: result, actionSucceeded: succeeded };
        }
        catch (err) {
            events.log(`Action error: ${err instanceof Error ? err.message : String(err)}`, 'error-msg');
            return { finalAction: retryAction, actionResult: `Error: ${err instanceof Error ? err.message : String(err)}`, actionSucceeded: false };
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
        if (!freshState)
            return resultText;
        const freshPlayer = freshState?.players?.[charName] || player;
        const currentArea = freshState.areas?.[freshPlayer?.current_area || freshState.current_area] || null;
        const roomContext = PromptBuilder.buildRoomContext(freshState, charName, freshPlayer, currentArea);
        events.logPhase(charName, 'decide', `${sourceVerb} follow-up`);
        VW?.ui?.setStatus?.("Chain follow-up...", "info");
        const prompt = PromptBuilder.buildChainFollowUpPrompt(charName, roomContext, resultText, sourceVerb, allowedVerbs);
        history.push({ role: 'user', content: prompt });
        const response = await this._callLLMMessages(history, 'chain-follow-up', charName);
        history.push({ role: 'assistant', content: response || '' });
        if (response === null)
            return resultText;
        const parsed = ResponseParser.parseReaction(response);
        if (parsed?.parseError) {
            events.logParseError(charName, 'chain-follow-up', parsed.parseError, response);
        }
        const followAction = parsed?.action || '';
        if (!followAction || this._checkCancel())
            return resultText;
        const verb = followAction.split(/\s+/)[0].toLowerCase();
        const exitNames = Object.keys(currentArea?.exits || {}).map(e => e.toLowerCase());
        const allowed = allowedVerbs.includes(verb);
        const isExitName = exitNames.includes(followAction.toLowerCase());
        if (!ActionNormalizer.isValidAction(followAction, charName) || (!allowed && !isExitName))
            return resultText;
        events.logPhase(charName, 'act', followAction);
        events.log(`[Action] ${followAction}`, "msg-action");
        try {
            const data = await agentApi.action(followAction, charName, { enforceSlots: true });
            if (data?.scenario_ended) {
                events.log("🏁 Scenario ended via trigger.", "system-msg");
                if (data?._restart_requested) {
                    events.log("🔄 Restarting scenario...", "system-msg");
                    await agentApi.resetWorld();
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
        }
        catch (err) {
            events.log(`${sourceVerb} follow-up error: ${err instanceof Error ? err.message : String(err)}`, 'error-msg');
            return resultText;
        }
    }
    /**
     * One automatic retry when a phase response came back as repaired/truncated
     * JSON (N1). The repair may have silently dropped fields (e.g. the emote);
     * re-asking once usually yields a complete reply. Never retries twice.
     */
    async _retryOnceOnParseError(charName, history, stepName, parser, parsed) {
        if (!parsed?.parseError || !history?.length)
            return parsed;
        // The message names the actual failure: a repaired/truncated reply and
        // a schema-invalid payload are different problems and want different
        // fixes from the model.
        const isSchemaError = /schema_invalid/.test(String(parsed.parseError));
        const reason = isSchemaError
            ? 'the action payload was malformed'
            : 'response was repaired (truncated JSON)';
        events.log(`⚠️ ${charName}: ${stepName} ${reason} - retrying once.`, 'error-msg');
        history.pop(); // drop the broken assistant message so the retry isn't seeded by it
        // A truncated reply usually repairs itself on a second ask. A schema
        // error does not: the model has to be told what the field must be,
        // or it reproduces the same malformed shape.
        if (isSchemaError) {
            history.push({ role: 'user', content: 'Your previous reply was rejected: the "action" field must be a single verb string (for example "action": "take"), never an object and never a sentence. Respond again with the same schema, with "action" as a plain verb string.' });
        }
        const retried = await this._callLLMMessages(history, stepName, charName);
        if (isSchemaError)
            history.pop(); // the correction is transient - do not keep it in the character history
        if (!retried) {
            history.push({ role: 'assistant', content: '' });
            return parsed;
        }
        history.push({ role: 'assistant', content: retried });
        const reparsed = parser(retried);
        if (reparsed && !reparsed.parseError)
            return reparsed;
        return parsed;
    }
    /** Thin wrapper: build message array and delegate to _callLLMMessages. */
    async _callLLM(prompt, history, stepName, actorName) {
        return this._callLLMMessages([...history, { role: 'user', content: prompt }], stepName, actorName);
    }
    /** Structured-output schema for a turn phase (task: structured output).
     *  The client drops it when disabled/unsupported, so null is a fine default. */
    _formatForStep(stepName) {
        const F = window.StructuredFormats;
        if (!F)
            return null;
        if (stepName === 'result-reaction')
            return F.agentReact;
        if (stepName === 'think-decide' || stepName === 'combined' || stepName === 'auto-retry' || stepName === 'chain-follow-up')
            return F.agentAction;
        return null;
    }
    // Send a pre-built message array as-is (system + accumulated history +
    // the new user message, already pushed by the caller). Pruned by the
    // context window when over the token/message limit.
    //
    // `actorName` is the character this call is FOR. The raw-LLM chips used
    // to guess the actor from "whose turn is it", which filed a prompt
    // written for one character under another one's name - the trace lied
    // about who was being asked what. The caller knows, so the caller says.
    async _callLLMMessages(messages, stepName, actorName) {
        // Pause is a turn-boundary gate: let the in-flight request finish, then
        // hold any later LLM phase here until the user resumes the run.
        while (config.running && this._paused) {
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        if (this._cancelRequested)
            return null;
        this.contextMgr.reset();
        messages.forEach((m, i) => this.contextMgr.addMessage(m, { importance: m.role === 'system' ? 2 : 0, type: m.role, keepAlways: m.role === 'system' }));
        const final = this.contextMgr.isOverLimit() ? this.contextMgr.prune(messages) : messages;
        // task-340: context pruning becomes a visible row instead of silent amnesia.
        const prunedCount = messages.length - final.length;
        if (prunedCount > 0) {
            const sig = `${stepName}:${prunedCount}`;
            if (this._lastPruneSig !== sig) {
                this._lastPruneSig = sig;
                events.log(`✂ Context pruned (${stepName}): dropped ${prunedCount} oldest messages`, 'msg-prune');
            }
        }
        else {
            this._lastPruneSig = null;
        }
        if (config.manualMode) {
            events.log(`✋ Manual mode - waiting for your response (${stepName})`, 'system-msg');
            return await this._showManualPrompt(final, stepName);
        }
        this._abortController = new AbortController();
        const streamId = `${stepName}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
        events.startStreaming(streamId, stepName);
        const onChunk = (c) => events.appendStream(streamId, c);
        // Correlation id: the request chip and its response chip carry the
        // same one, so a reader can pair them up without guessing from
        // ordering.
        const requestId = `${stepName}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
        // Fix 6: add 120s timeout so a stalled LLM doesn't hang the agent forever
        const LLM_TIMEOUT_MS = 120000;
        try {
            const chatPromise = llmClient.chat(final, { streaming: config.streaming, max_tokens: config.maxTokens, signal: this._abortController.signal, onChunk, label: stepName, responseFormat: this._formatForStep(stepName), actor: actorName, requestId });
            const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('LLM timeout')), LLM_TIMEOUT_MS));
            const r = await Promise.race([chatPromise, timeoutPromise]);
            this._abortController = null;
            events.finishStreaming(streamId, r);
            return r;
        }
        catch (err) {
            // AbortError is what fetch() rejects with on abort; read the flag off
            // whatever was thrown rather than requiring an Error instance.
            const errName = err?.name;
            if (errName === 'AbortError') {
                events.finishStreaming(streamId);
                events.log('⏹️ LLM call cancelled.', 'system-msg');
                return null;
            }
            if (err instanceof Error && err.message === 'LLM timeout') {
                events.log(`⏱️ LLM call timed out after ${LLM_TIMEOUT_MS / 1000}s (${stepName})`, 'error-msg');
                events.finishStreaming(streamId);
                return null;
            }
            events.log(`LLM error (${stepName}): ${err instanceof Error ? err.message : String(err)}`, "error-msg");
            events.finishStreaming(streamId);
            return null;
        }
    }
}
// Singleton.
// globals.d.ts already declares a global `agent` (hoisted there for the modules
// that read `agent.turnQueue`), so a top-level `const agent` here would be a
// redeclaration and fail the build. Assigning the singleton onto the global
// object instead gives those readers the same bare `agent` binding: a
// global-object property resolves as a bare identifier in every classic script.
// The only difference is binding kind - the name is now an own property of
// `window` rather than a script-scoped lexical binding. The documented access
// path is `VW.agent` (main.ts assigns `VW.agent = agent`).
window.agent = new AgentEngine();
