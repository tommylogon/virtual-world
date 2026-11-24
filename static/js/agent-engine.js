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
const NOOP_ACTIONS = ['wait', 'nothing', 'pause', 'stay'];
// task-104: after a SUCCESSFUL action, the agent may chain ONE immediate
// follow-up from the actionWord list (same-turn, like the original dash chain).
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
        this._recentInnerMonologues = {};
    }
    get isPaused() { return this._paused; }
    getHistory(charName) {
        if (!this.characterHistories[charName]) {
            this.characterHistories[charName] = [{ role: 'system', content: '' }];
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
        return NOOP_ACTIONS.includes((action || '').split(' ')[0].toLowerCase());
    }
    async _speakLine(charName, player, speech, volume = 'say', target = null, tone = null) {
        const spokenVolume = volume || 'say';
        const spokenTone = tone ? (ActionNormalizer?.normalizeSpeechTone?.(tone) || null) : null;
        events.trackPhase(charName, 'speech', { speech, volume: spokenVolume, target, tone: spokenTone });
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
        // Optional delivery tone (task-994) uses the same `[tone:<val>]` prefix convention as `[lang:<val>]`.
        const directed = spokenVolume === 'whisper' && target;
        const tonePrefix = spokenTone ? `[tone:${spokenTone}] ` : '';
        const command = directed
            ? `whisper to ${target}: ${tonePrefix}${speech}`
            : `${spokenVolume} ${tonePrefix}${speech}`;
        const speakerName = player?.name || charName;
        const toneAdv = spokenTone ? (ActionNormalizer?.toneAdverb?.(spokenTone) || '') : '';
        const toneTag = toneAdv ? ` (${toneAdv})` : '';
        try {
            const data = await agentApi.action(command, charName);
            const output = (data && data.output) || '';
            const blocked = (data && data.success === false) ||
                /no sound comes out|can't move or act|can't do that/i.test(output);
            if (blocked) {
                events.log(`🔇 ${speakerName}: ${output.trim() || 'cannot speak.'}`, 'error-msg');
            }
            else if (directed) {
                // task-340: whispered lines get a distinct locked row in the stream.
                events.log(`🔒 ${speakerName} → ${target}${toneTag}: "${speech}"`, "msg-whisper");
            }
            else {
                events.log(`[${speakerName}] ${ActionNormalizer.volAction(spokenVolume)}${toneTag}: "${speech}"`, "msg-speech");
            }
        }
        catch (err) {
            events.log(`[${speakerName}] ${ActionNormalizer.volAction(spokenVolume)}${toneTag}: "${speech}"`, "msg-speech");
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
    _storeReactionMemory(charName, memory, feltEmotion = null, actionSucceeded = true, actionResult = '', actionString = '') {
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
        const entityIdsSet = new Set();
        if (entityId)
            entityIdsSet.add(entityId);
        if (Array.isArray(memory.entity_ids)) {
            for (const id of memory.entity_ids)
                if (id)
                    entityIdsSet.add(String(id));
        }
        if (Array.isArray(memory.entities)) {
            for (const e of memory.entities)
                if (e)
                    entityIdsSet.add(String(e));
        }
        if (actionString) {
            const actWords = actionString.toLowerCase().split(/\s+/).slice(1);
            const joinedTarget = actWords.join(' ');
            const allPlayers = worldState.data?.players || {};
            for (const pname of Object.keys(allPlayers)) {
                if (pname !== charName && (pname.toLowerCase() === joinedTarget || actWords.includes(pname.toLowerCase()))) {
                    entityIdsSet.add('player_' + pname.toLowerCase());
                }
            }
            const roomItems = (typeof worldState.getItemsInArea === 'function' && player?.current_area)
                ? (worldState.getItemsInArea(player.current_area) || []) : [];
            const allItems = [...roomItems, ...(player?.inventory || [])];
            for (const item of allItems) {
                const iid = typeof item === 'object' && item?.id ? String(item.id) : null;
                const iname = typeof item === 'object' && item?.name ? String(item.name).toLowerCase() : (typeof item === 'string' ? item.toLowerCase() : '');
                if (iname && (joinedTarget.includes(iname) || actWords.includes(iname))) {
                    if (iid)
                        entityIdsSet.add(iid);
                    else
                        entityIdsSet.add('item_' + iname.replace(/\s+/g, '_'));
                }
            }
        }
        const location = player?.current_area || entityId || '';
        const extraProps = {};
        if (memory.category)
            extraProps.category = memory.category;
        if (memory.confidence !== undefined)
            extraProps.confidence = memory.confidence;
        if (memory.about)
            extraProps.about = memory.about;
        if (memory.hypotheses)
            extraProps.hypotheses = memory.hypotheses;
        if (memory.status)
            extraProps.status = memory.status;
        if (memory.watch_refs)
            extraProps.watch_refs = memory.watch_refs;
        if (memory.valid_at !== undefined)
            extraProps.valid_at = memory.valid_at;
        if (memory.invalid_at !== undefined)
            extraProps.invalid_at = memory.invalid_at;
        const primaryEmotion = Array.isArray(feltEmotion) ? (feltEmotion[0] || null) : feltEmotion;
        window.AgentMemory.storeMemory(charName, memory.text, memory.importance, 'reaction', tick, Array.from(entityIdsSet), memory.tags, primaryEmotion, memory.emotions || null, location, extraProps);
    }
    /**
     * Persist Actor inner monologue as a reflection memory (task-948).
     * Deduplicates identical text within +/- 1 tick so repeated inner phrases
     * in the same turn are not written twice.
     */
    _persistInnerMonologue(charName, inner, feltEmotion = null) {
        const rawText = String(inner || '').trim();
        if (!charName || !rawText)
            return;
        const pb = window.PromptBuilder;
        const am = window.AgentMemory;
        const normalizer = am?.normalizeMemoryText || pb?.normalizeMemoryText;
        const text = normalizer ? normalizer(rawText) : rawText.replace(/^\[[^\]]+\]\s*/, '').trim();
        if (!text)
            return;
        const tick = worldState.runtimeData?.time_ticks ?? worldState.data?.time_ticks ?? 0;
        const normalizedKey = text.toLowerCase();
        const last = this._recentInnerMonologues?.[charName];
        if (last && last.text === normalizedKey && Math.abs(last.tick - tick) <= 1)
            return;
        const player = worldState.runtimePlayer?.(charName) || worldState.data?.players?.[charName];
        const duplicate = (player?.memories || []).some((existing) => {
            const existingNorm = (normalizer ? normalizer(existing.text || '') : String(existing.text || '')).trim().toLowerCase();
            const sameTick = Math.abs((existing.tick || 0) - tick) <= 1;
            return existingNorm === normalizedKey && sameTick;
        });
        if (duplicate)
            return;
        if (!this._recentInnerMonologues)
            this._recentInnerMonologues = {};
        this._recentInnerMonologues[charName] = { text: normalizedKey, tick };
        const entityId = this._currentAreaEntityId(charName);
        const entityIds = entityId ? [entityId] : [];
        const location = player?.current_area || entityId || '';
        const primaryEmotion = Array.isArray(feltEmotion) ? (feltEmotion[0] || null) : feltEmotion;
        const emoInt = Number(primaryEmotion?.intensity);
        const importance = Number.isFinite(emoInt) ? Math.max(5, Math.min(8, Math.round(emoInt))) : 5;
        if (typeof am?.storeMemory === 'function') {
            am.storeMemory(charName, text, importance, 'reflection', tick, entityIds, ['inner_monologue', 'thought'], primaryEmotion || null, null, location, { source: 'inner_monologue', category: 'reflection' });
            return;
        }
        if (typeof ApiClient !== 'undefined' && typeof ApiClient.addPlayerMemory === 'function') {
            ApiClient.addPlayerMemory(charName, {
                text,
                tick,
                importance,
                type: 'reflection',
                category: 'reflection',
                source: 'inner_monologue',
                entity_ids: entityIds,
                tags: ['inner_monologue', 'thought'],
                emotion: (primaryEmotion && typeof primaryEmotion === 'object')
                    ? { label: primaryEmotion.label, intensity: primaryEmotion.intensity }
                    : null,
                location,
                valid_at: tick,
                invalid_at: null,
            }).catch(() => { });
        }
    }
    /**
     * Fire-and-forget spike of the character's affect map from an LLM-declared
     * feeling (task-96, bug-596). Silent no-op when absent/malformed or backend misses.
     */
    _applyFeltEmotion(charName, emotion) {
        if (!emotion || !worldState.players?.[charName])
            return null;
        const impulses = (Array.isArray(emotion) ? emotion : [emotion]).filter((e) => Boolean(e && typeof e === 'object' && e.label));
        if (!impulses.length)
            return null;
        const dispatches = [];
        for (const imp of impulses) {
            const label = String(imp.label).trim();
            if (!label)
                continue;
            const rawIntensity = Number(imp.intensity);
            const intensity = Number.isFinite(rawIntensity) ? Math.max(1, Math.min(10, rawIntensity)) : 5;
            // task-350: when the feeling is TOWARD a specific person, pass `toward`
            // so the backend records it as an experience (felt_toward) and so
            // relationships/feelings can change toward that person. Otherwise it's
            // a global affect spike (legacy).
            const body = { emotion: label, intensity };
            if (imp.toward)
                body.toward = String(imp.toward).trim();
            else
                body.delta = intensity * 1.5;
            try {
                const req = ApiClient.getPlayerEmotions(charName, body);
                if (req && typeof req.catch === 'function') {
                    dispatches.push(req.catch(() => { }));
                }
            }
            catch (e) { /* ignore */ }
        }
        if (!dispatches.length)
            return null;
        return dispatches.length === 1 ? dispatches[0] : Promise.all(dispatches);
    }
    /** task-350: record names the agent confirmed/deduced this turn (heard,
     *  name tag, sign, document, deduction). Fire-and-forget; engine validates
     *  they are real present players so the agent cannot invent a name tag. */
    _learnNames(charName, learnedNames) {
        if (!learnedNames?.length || !worldState.players?.[charName])
            return;
        try {
            return ApiClient.getPlayerNames(charName, learnedNames).catch(() => { });
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
                const picked = step;
                if (picked.inner) {
                    events.logThought(charName, picked.inner, worldState.tick);
                    events.trackPhase?.(charName, 'think', { thought: picked.inner });
                }
                if (picked.emotion) {
                    const firstEmo = Array.isArray(picked.emotion) ? picked.emotion[0] : picked.emotion;
                    const emoVal = typeof firstEmo === 'object' && firstEmo
                        ? firstEmo.label
                        : (firstEmo ? String(firstEmo) : '');
                    if (emoVal) {
                        ApiClient.updateCharacter(charName, { emotion: emoVal }).catch(() => { });
                    }
                    this._applyFeltEmotion(charName, picked.emotion);
                }
                const res = await this._executeHumanReply(charName, currentPlayer, step);
                if (res.text)
                    results.push(res.text);
                await worldState.fetchRuntime();
                const currentArea = worldState.runtimePlayer(charName)?.current_area;
                if (currentArea)
                    agentConfig.lastRoom[charName] = currentArea;
                if (step.memory?.text)
                    this._storeReactionMemory(charName, { text: step.memory.text, ...(step.memory || {}) }, null, true, '', step.action || '');
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
                // empty `action_points` (`{}`) is the "not started" sentinel the engine
                // lazily fills; treating it as spent ended the human turn after one
                // step and refused the next action.
                const slots = worldState.runtimePlayer(charName)?.action_points;
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
                    if (reaction.inner) {
                        events.logThought(charName, reaction.inner, worldState.tick);
                        events.trackPhase?.(charName, 'think', { thought: reaction.inner });
                    }
                    if (reaction.emotion) {
                        const firstEmo = Array.isArray(reaction.emotion) ? reaction.emotion[0] : reaction.emotion;
                        const emoVal = typeof firstEmo === 'object' && firstEmo
                            ? firstEmo.label
                            : (firstEmo ? String(firstEmo) : '');
                        if (emoVal) {
                            ApiClient.updateCharacter(charName, { emotion: emoVal }).catch(() => { });
                        }
                        this._applyFeltEmotion(charName, reaction.emotion);
                    }
                    if (reaction.speech) {
                        await this._speakLine(charName, currentPlayer, reaction.speech, reaction.volume, reaction.target, reaction.tone || reaction.speechTone || null);
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
    buildSystemPrompt(_charName, _opts) {
        return '';
    }
    buildContextPrompt(charName, _opts) {
        const state = worldState.runtimeData || worldState.data || {};
        const player = worldState.runtimePlayer?.(charName) || state.players?.[charName] || worldState.players?.[charName] || {};
        const area = player?.current_area || state.current_area || 'unknown';
        return `You are ${charName} in ${area}.`;
    }
    async callLLM(systemPrompt, messages, charName, stepName) {
        return this._callLLMMessages([{ role: 'system', content: systemPrompt }, ...messages], stepName, charName);
    }
    /**
     * Collect canonical entity names (items, people, ways) for grounding
     * Director drafts against the actual scene and inventory (task-942).
     */
    _collectCanonicalSceneEntities(charName, state, player, currentArea, scene) {
        const itemsSet = new Set();
        const peopleSet = new Set();
        const waysSet = new Set();
        const addName = (set, raw) => {
            if (!raw)
                return;
            const s = typeof raw === 'string'
                ? raw.trim()
                : String(raw.name || raw.display_name || raw.id || '').trim();
            if (s && s.toLowerCase() !== 'none')
                set.add(s);
        };
        const toList = (val) => {
            if (!val)
                return [];
            if (Array.isArray(val))
                return val;
            if (typeof val === 'object') {
                return Object.entries(val).map(([k, v]) => (v && typeof v === 'object') ? { id: k, direction: k, ...v } : (typeof v === 'string' && v.trim() ? v : k));
            }
            return [];
        };
        if (scene && typeof scene === 'object') {
            for (const it of toList(scene.items))
                addName(itemsSet, it);
            for (const inv of [...toList(scene.you?.carrying), ...toList(scene.you?.wearing)])
                addName(itemsSet, inv);
            for (const p of toList(scene.people))
                addName(peopleSet, p?.display_name || p?.name || p);
            for (const w of toList(scene.ways)) {
                addName(waysSet, w?.direction);
                addName(waysSet, w?.to);
                addName(waysSet, w?.name);
            }
        }
        for (const inv of [...toList(player?.inventory), ...toList(player?.carrying)])
            addName(itemsSet, inv);
        if (player?.equipped && typeof player.equipped === 'object') {
            for (const eq of Object.values(player.equipped))
                addName(itemsSet, eq);
        }
        for (const it of toList(currentArea?.items))
            addName(itemsSet, it);
        for (const ch of toList(currentArea?.characters || currentArea?.people)) {
            const n = typeof ch === 'string' ? ch : (ch?.name || ch?.display_name || ch?.id);
            if (n && String(n).toLowerCase() !== charName.toLowerCase())
                addName(peopleSet, n);
        }
        const areaKey = player?.current_area || currentArea?.id || currentArea?.name || state?.current_area;
        if (areaKey && state?.players && typeof state.players === 'object') {
            for (const [pName, pObj] of Object.entries(state.players)) {
                if (pName.toLowerCase() !== charName.toLowerCase() && pObj?.current_area === areaKey) {
                    addName(peopleSet, pName);
                }
            }
        }
        if (currentArea?.exits && typeof currentArea.exits === 'object' && !Array.isArray(currentArea.exits)) {
            for (const [dir, dest] of Object.entries(currentArea.exits)) {
                addName(waysSet, dir);
                if (typeof dest === 'string')
                    addName(waysSet, dest);
                else if (dest && typeof dest === 'object') {
                    addName(waysSet, dest.to || dest.target || dest.area || dest.name);
                }
            }
        }
        else {
            for (const ex of toList(currentArea?.exits || currentArea?.ways)) {
                if (typeof ex === 'string')
                    addName(waysSet, ex);
                else if (ex && typeof ex === 'object') {
                    addName(waysSet, ex.direction);
                    addName(waysSet, ex.to);
                    addName(waysSet, ex.name);
                }
            }
        }
        return {
            items: Array.from(itemsSet),
            people: Array.from(peopleSet),
            ways: Array.from(waysSet),
        };
    }
    /**
     * Match a potentially fuzzy LLM entity reference (e.g. "phone case" or "Kayla")
     * against canonical entity names in the scene/inventory (task-942).
     */
    _matchCanonicalEntity(rawRef, candidates) {
        const clean = (rawRef || '').trim();
        if (!clean || !candidates || !candidates.length)
            return clean;
        const lower = clean.toLowerCase();
        for (const c of candidates) {
            if (c.toLowerCase() === lower)
                return c;
        }
        const STOP = new Set(['the', 'a', 'an', 'my', 'his', 'her', 'their', 'your', 'our', 'some', 'this', 'that']);
        const tokenize = (s) => s.toLowerCase()
            .replace(/['’]s\b/g, '')
            .replace(/[^a-z0-9]+/g, ' ')
            .split(/\s+/)
            .filter(tok => tok.length >= 2 && !STOP.has(tok));
        const refTokens = tokenize(clean);
        if (!refTokens.length)
            return clean;
        let bestCandidate = clean;
        let bestOverlap = 0;
        let bestSub = false;
        let bestRatio = 0;
        for (const c of candidates) {
            const cLower = c.toLowerCase();
            const cTokens = tokenize(c);
            if (!cTokens.length)
                continue;
            let overlap = 0;
            for (const rt of refTokens) {
                if (cTokens.some(ct => ct === rt || (ct.length >= 4 && rt.length >= 4 && (ct.includes(rt) || rt.includes(ct))))) {
                    overlap++;
                }
            }
            const isSub = cLower.includes(lower) || lower.includes(cLower);
            const ratio = overlap / cTokens.length;
            if (overlap > bestOverlap ||
                (overlap === bestOverlap && overlap > 0 && (isSub && !bestSub || (isSub === bestSub && ratio > bestRatio))) ||
                (bestOverlap === 0 && isSub && !bestSub)) {
                bestOverlap = overlap;
                bestSub = isSub;
                bestRatio = ratio;
                bestCandidate = c;
            }
        }
        return (bestOverlap >= 1 || bestSub) ? bestCandidate : clean;
    }
    /**
     * Ground fuzzy entity names in a Director draft's `action` and `target`
     * against canonical scene/inventory entities, and infer directed speech
     * target / volume from the Director's Note or vocative speech prefix when
     * small local models omit them (task-942).
     */
    _groundDirectorDraft(charName, state, player, currentArea, draft, scene, directorNote) {
        const entities = this._collectCanonicalSceneEntities(charName, state, player, currentArea, scene);
        const allItems = entities.items;
        const allPeople = entities.people;
        const allWays = entities.ways;
        const allEntities = [...allItems, ...allPeople, ...allWays];
        let groundedVolume = draft.speechVolume || 'say';
        const noteText = (directorNote || '').trim();
        if (draft.speech && noteText && groundedVolume === 'say') {
            if (/\bwhisper(?:s|ing|ed)?\b/i.test(noteText))
                groundedVolume = 'whisper';
            else if (/\bscream(?:s|ing|ed)?\b/i.test(noteText))
                groundedVolume = 'scream';
            else if (/\bshout(?:s|ing|ed)?\b|\byell(?:s|ing|ed)?\b/i.test(noteText))
                groundedVolume = 'shout';
        }
        let groundedTarget = null;
        if (draft.target) {
            if (allPeople.length > 0) {
                const candidatePerson = this._matchCanonicalEntity(draft.target, allPeople);
                const matchesItemOnly = allItems.some(it => it.toLowerCase() === candidatePerson.toLowerCase());
                groundedTarget = matchesItemOnly ? null : candidatePerson;
            }
            else {
                const matchesItemOrWay = [...allItems, ...allWays].some(it => {
                    const m = this._matchCanonicalEntity(draft.target, [it]);
                    return m === it && m.toLowerCase() !== draft.target.toLowerCase();
                });
                groundedTarget = matchesItemOrWay ? null : draft.target;
            }
        }
        if (!groundedTarget && draft.speech && allPeople.length > 0) {
            const findPersonInText = (txt, requireVocative = false) => {
                if (!txt)
                    return null;
                const lowerTxt = txt.toLowerCase();
                const matches = [];
                for (const p of allPeople) {
                    const pLower = p.toLowerCase();
                    const firstTok = pLower.split(/\s+/)[0];
                    if (requireVocative) {
                        const vocRe = new RegExp(`^["'\\s]*(?:${pLower.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}|${firstTok.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})\\b\\s*[,!?:\\-]`, 'i');
                        if (vocRe.test(txt))
                            matches.push(p);
                    }
                    else {
                        const wordRe = new RegExp(`\\b(?:${pLower.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}|${firstTok.length >= 3 ? firstTok.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') : pLower.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})\\b`, 'i');
                        if (wordRe.test(lowerTxt))
                            matches.push(p);
                    }
                }
                return matches.length === 1 ? matches[0] : null;
            };
            groundedTarget = findPersonInText(noteText, false) || findPersonInText(draft.speech, true);
        }
        const act = (draft.action || '').trim();
        if (!act)
            return { action: '', target: groundedTarget, speechVolume: groundedVolume };
        const spaceIdx = act.search(/\s/);
        if (spaceIdx < 0)
            return { action: act, target: groundedTarget, speechVolume: groundedVolume };
        const actionWord = act.slice(0, spaceIdx).toLowerCase();
        const rest = act.slice(spaceIdx + 1).trim();
        if (!rest)
            return { action: act, target: groundedTarget, speechVolume: groundedVolume };
        if (actionWord === 'give' || actionWord === 'steal' || actionWord === 'teach') {
            const m = rest.match(/^(.+?)\s+(to|from)\s+(.+)$/i);
            if (m) {
                const itemGrounded = this._matchCanonicalEntity(m[1], allItems.length ? allItems : allEntities);
                const prep = m[2].toLowerCase();
                const targGrounded = this._matchCanonicalEntity(m[3], allPeople.length ? allPeople : allEntities);
                return { action: `${actionWord} ${itemGrounded} ${prep} ${targGrounded}`, target: groundedTarget, speechVolume: groundedVolume };
            }
        }
        if (actionWord === 'use') {
            const m = rest.match(/^(.+?)\s+on\s+(.+)$/i);
            if (m) {
                const itemGrounded = this._matchCanonicalEntity(m[1], allItems.length ? allItems : allEntities);
                const targGrounded = this._matchCanonicalEntity(m[2], allEntities);
                return { action: `use ${itemGrounded} on ${targGrounded}`, target: groundedTarget, speechVolume: groundedVolume };
            }
        }
        if (actionWord === 'go' || actionWord === 'crawl' || actionWord === 'climb' || actionWord === 'jump' || actionWord === 'dash') {
            const wayGrounded = this._matchCanonicalEntity(rest, allWays.length ? allWays : allEntities);
            return { action: `${actionWord} ${wayGrounded}`, target: groundedTarget, speechVolume: groundedVolume };
        }
        if (actionWord === 'approach' || actionWord === 'attack' || actionWord === 'lead' || actionWord === 'kiss' || actionWord === 'caress' || actionWord === 'follow') {
            const pool = [...allPeople, ...allItems, ...allWays];
            return { action: `${actionWord} ${this._matchCanonicalEntity(rest, pool)}`, target: groundedTarget, speechVolume: groundedVolume };
        }
        const itemPool = [...allItems, ...allWays, ...allPeople];
        return { action: `${actionWord} ${this._matchCanonicalEntity(rest, itemPool)}`, target: groundedTarget, speechVolume: groundedVolume };
    }
    /**
     * Build and inject the `[CURRENT DRAFT IN COMPOSER]` and
     * `[MANDATORY DIRECTOR STEERING NOTE]` blocks right before the JSON schema
     * instruction so small/local models prioritize the Director's Note (task-942).
     */
    _injectDirectorSteering(basePrompt, note, currentDraft, _entities) {
        const blocks = [];
        if (currentDraft && typeof currentDraft === 'object') {
            const draftLines = [];
            if (currentDraft.action)
                draftLines.push(`- ACTION: ${currentDraft.action}`);
            if (currentDraft.speech) {
                const vol = currentDraft.speechVolume || 'say';
                const tgt = currentDraft.target ? `, target: ${currentDraft.target}` : '';
                draftLines.push(`- SAY (${vol}${tgt}): "${currentDraft.speech}"`);
            }
            if (currentDraft.emote)
                draftLines.push(`- EMOTE: ${currentDraft.emote}`);
            if (currentDraft.inner)
                draftLines.push(`- THOUGHT: ${currentDraft.inner}`);
            if (currentDraft.emotion) {
                const draftEmo = typeof currentDraft.emotion === 'string'
                    ? currentDraft.emotion
                    : JSON.stringify(currentDraft.emotion);
                draftLines.push(`- EMOTION: ${draftEmo}`);
            }
            if (currentDraft.memory)
                draftLines.push(`- MEMORY: ${currentDraft.memory}`);
            if (draftLines.length > 0) {
                blocks.push(`[CURRENT DRAFT IN COMPOSER (PREVIOUS TAKE)]:\n${draftLines.join('\n')}\n` +
                    (note
                        ? `Refine or adjust this previous take according to the Director Steering Note below (keeping any parts the note asks to keep, and rewriting any parts the note asks to change).`
                        : `Propose a fresh alternative take that varies from this current draft while staying in character.`));
            }
        }
        if (note) {
            blocks.push(`[DIRECTOR STEERING NOTE]: ${note}\n` +
                `Incorporate this direction into your chosen ACTION, SAY, EMOTE, THOUGHT, EMOTION, and MEMORY.`);
        }
        if (!blocks.length)
            return basePrompt;
        return `${basePrompt}\n\n${blocks.join('\n\n')}`;
    }
    /**
     * Stateless AI Director turn draft helper (task-933, task-942).
     * Can be invoked on demand from HumanTurnComposer ("Ask Director") or
     * automatically when a character with auto-draft enabled starts a turn.
     */
    async draftTurnForCharacter(charName, opts) {
        if ((!config.apiKey && !config.apiBase?.includes('localhost') && !config.apiBase?.includes('127.0.0.1')) || !config.model) {
            events.log('No API key/model configured for Director draft.', 'error-msg');
            return null;
        }
        if (worldState._runtimeFocus?.length && typeof worldState.fetchRuntime === 'function') {
            await worldState.fetchRuntime();
        }
        else if (typeof worldState.fetch === 'function') {
            await worldState.fetch();
        }
        const state = worldState.runtimeData || worldState.data || {};
        const player = worldState.runtimePlayer?.(charName) || state.players?.[charName] || worldState.players?.[charName] || {};
        const currentArea = state.areas?.[player?.current_area || state.current_area] || null;
        const note = (opts?.directorNote || '').trim();
        const entities = this._collectCanonicalSceneEntities(charName, state, player, currentArea, opts?.scene);
        const memoryNL = PromptBuilder?.buildMemoryContext ? await PromptBuilder.buildMemoryContext(charName, { report: false }) : '';
        if (opts?.phase === 'react') {
            const pyReact = await ApiClient.getAgentPrompt?.({
                character: charName,
                phase: 'react',
                what_happened: opts?.actionResult || 'Nothing notable happened.',
                memory_thought: memoryNL || '',
                action_points: player?.action_points || undefined,
            }).catch(() => null);
            const systemPrompt = pyReact?.messages?.[0]?.content || '';
            let reactPrompt = pyReact?.messages?.[1]?.content || opts?.actionResult || 'Nothing notable happened.';
            reactPrompt = this._injectDirectorSteering(reactPrompt, note, opts?.currentDraft, entities);
            const raw = await this.callLLM(systemPrompt, [{ role: 'user', content: reactPrompt }], charName, 'director-react');
            if (!raw)
                return null;
            const parsed = (ResponseParser.parseReaction ? ResponseParser.parseReaction(raw) : ResponseParser.parseResultReaction?.(raw)) || {};
            const grounded = this._groundDirectorDraft(charName, state, player, currentArea, {
                action: '',
                target: parsed.target || null,
                speech: parsed.speech || null,
                speechVolume: parsed.speechVolume || 'say',
            }, opts?.scene, note);
            const memVal = typeof parsed.memory === 'object' && parsed.memory
                ? parsed.memory.text || null
                : (parsed.memory || null);
            return {
                action: null,
                speech: parsed.speech || null,
                speechVolume: grounded.speechVolume,
                target: grounded.target,
                emote: parsed.emote || null,
                inner: parsed.inner || null,
                emotion: parsed.emotion || null,
                memory: memVal,
            };
        }
        const pyThink = await ApiClient.getAgentPrompt?.({
            character: charName,
            phase: 'think',
            last_result: opts?.actionResult || agentConfig.lastActionResult?.[charName] || '',
            memory_thought: memoryNL || '',
            action_points: this._turnSlots?.[charName] || player?.action_points || undefined,
        }).catch(() => null);
        const systemPrompt = pyThink?.messages?.[0]?.content || '';
        let decidePrompt = pyThink?.messages?.[1]?.content || '';
        if (!decidePrompt) {
            decidePrompt = this.buildContextPrompt(charName);
        }
        decidePrompt = this._injectDirectorSteering(decidePrompt, note, opts?.currentDraft, entities);
        const raw = await this.callLLM(systemPrompt, [{ role: 'user', content: decidePrompt }], charName, 'director-draft');
        if (!raw)
            return null;
        // If interpreter is enabled (task-943), pass raw LLM text through ActionInterpreter
        // to transcribe character thoughts, speech, and actions into canonical engine format
        const win = window;
        let parsed = null;
        if (config.interpreterModelEnabled && win.ActionInterpreter && typeof win.ActionInterpreter.interpretProseToAction === 'function') {
            const context = this._buildInterpreterContext(charName, state, player, currentArea);
            const interpreted = await win.ActionInterpreter.interpretProseToAction({
                prose: raw,
                charName,
                context,
                directorNote: note
            });
            if (interpreted) {
                parsed = {
                    action: interpreted.action,
                    item: interpreted.item,
                    target: interpreted.target,
                    speech: interpreted.speech,
                    speechVolume: interpreted.speechVolume,
                    emote: interpreted.emote,
                    inner: interpreted.inner_monologue,
                    emotion: interpreted.emotion,
                    memory: interpreted.memory
                };
            }
        }
        if (!parsed) {
            parsed = ResponseParser.parseReaction(raw) || {};
        }
        const actRaw = typeof parsed.action === 'string' ? parsed.action.trim() : '';
        const normAction = actRaw && actRaw.toLowerCase() !== 'none' ? actRaw : '';
        const grounded = this._groundDirectorDraft(charName, state, player, currentArea, {
            action: normAction,
            target: parsed.target || parsed.item || null,
            speech: parsed.speech || null,
            speechVolume: parsed.speechVolume || 'say',
        }, opts?.scene, note);
        const memVal = typeof parsed.memory === 'object' && parsed.memory
            ? parsed.memory.text || null
            : (parsed.memory || null);
        return {
            action: grounded.action,
            speech: parsed.speech || null,
            speechVolume: grounded.speechVolume,
            target: grounded.target,
            emote: parsed.emote || null,
            inner: parsed.inner || parsed.inner_monologue || null,
            emotion: parsed.emotion || null,
            memory: memVal,
        };
    }
    /**
     * Build a visibility-aware context for ActionInterpreter (bug-597).
     * Filters hidden items, respects dim/pitch_black light rules, excludes hidden
     * characters, and masks unmet strangers via PromptBuilder.anonymousName.
     */
    _buildInterpreterContext(charName, state, player, currentArea) {
        const waysOut = [];
        if (currentArea?.ways) {
            for (const [wName, wObj] of Object.entries(currentArea.ways)) {
                waysOut.push({
                    name: wName,
                    destination: wObj.to || wObj.destination || '',
                    direction: wObj.direction || ''
                });
            }
        }
        const areaName = currentArea?.name || player?.current_area || state?.current_area || '';
        const light = currentArea?.ambient_light
            ?? currentArea?.environment?.light ?? 50;
        const level = typeof PromptBuilder?.lightToLevel === 'function'
            ? PromptBuilder.lightToLevel(light)
            : (Number(light) <= 20 ? 'pitch_black' : Number(light) <= 40 ? 'dim' : 'normal');
        const traits = player?.traits || {};
        const hasDarkVision = traits.dark_vision === true || traits.darkvision === true;
        const isBlind = !!(player?.conditions?.blind);
        const hasGraph = !!worldState?.data?.graph?.nodes;
        let rawAreaItems = [];
        if (areaName && typeof worldState?.getItemsInArea === 'function') {
            rawAreaItems = worldState.getItemsInArea(areaName) || [];
        }
        if (!rawAreaItems.length && !hasGraph && currentArea?.items && typeof currentArea.items === 'object') {
            rawAreaItems = Object.entries(currentArea.items).map(([k, v]) => {
                if (v && typeof v === 'object') {
                    return {
                        id: v.id || k,
                        name: v.name || k,
                        properties: v.properties || v,
                    };
                }
                return { id: k, name: k, properties: {} };
            });
        }
        let visibleItems = rawAreaItems.filter(it => it && it.name && it.properties?.current_state !== 'hidden');
        if (isBlind) {
            const memIdx = player?.memory_index || {};
            const knownItemNames = new Set();
            if (Array.isArray(player?.memories)) {
                for (const m of player.memories) {
                    if (m && m.kind === 'item' && m.name)
                        knownItemNames.add(String(m.name).toLowerCase().trim());
                }
            }
            visibleItems = visibleItems.filter(it => (it.id && memIdx[String(it.id)]) || knownItemNames.has(String(it.name || '').toLowerCase().trim()));
        }
        else if (!hasDarkVision) {
            if (level === 'pitch_black') {
                visibleItems = [];
            }
            else if (level === 'dim') {
                visibleItems = visibleItems.filter(it => ((it.properties?.weight || 1) >= 3));
            }
        }
        const thingsVisible = visibleItems.map(it => String(it.name)).filter(Boolean);
        const allPlayers = state?.players || {};
        const rawPeople = (typeof window.PromptBuilder?.playersInAreaFor === 'function')
            ? window.PromptBuilder.playersInAreaFor(state, charName, areaName)
            : Object.entries(allPlayers).map(([pName, pData]) => ({
                name: pName,
                ...(pData && typeof pData === 'object' ? pData : {}),
            })).filter((p) => p.current_area === areaName && p.name !== charName);
        const isPersonHidden = (person) => {
            const pName = person?.name;
            const pData = (pName && allPlayers[pName]) || {};
            return !!(person?.hidden
                || person?.conditions?.hidden
                || person?.current_state === 'hidden'
                || pData?.hidden
                || pData?.conditions?.hidden
                || pData?.current_state === 'hidden');
        };
        const peopleHere = [];
        for (const person of rawPeople) {
            if (!person)
                continue;
            const pName = person.name;
            if (pName === charName)
                continue;
            if (isPersonHidden(person))
                continue;
            const rawDesc = String(person.description || (pName && allPlayers[pName]?.description) || '').trim();
            const firstSentence = rawDesc ? rawDesc.split(/[.!?]/)[0].trim() : '';
            const desc = firstSentence ? firstSentence + (rawDesc.includes('.') ? '.' : '') : '';
            let displayName;
            if (pName) {
                displayName = typeof PromptBuilder?.anonymousName === 'function'
                    ? PromptBuilder.anonymousName(charName, pName, desc)
                    : (person.unknown_display_name || (firstSentence ? `the ${firstSentence.toLowerCase()}` : 'the stranger'));
            }
            else {
                displayName = person.display_name || person.unknown_display_name || 'the stranger';
            }
            if (displayName)
                peopleHere.push(displayName);
        }
        const inventory = Object.keys(player?.inventory || {});
        return { waysOut, thingsVisible, peopleHere, inventory };
    }
    /**
     * Interpret raw creative character prose into a structured engine turn (task-943).
     * Pluggable service method utilizing the dedicated or active interpreter model.
     */
    async interpretProseToDraft(charName, prose, opts) {
        const interpreter = window.ActionInterpreter;
        if (!interpreter || typeof interpreter.interpretProseToAction !== 'function') {
            events.log('ActionInterpreter not loaded in window.', 'error-msg');
            return null;
        }
        const state = worldState.runtimeData || worldState.data || {};
        const player = worldState.runtimePlayer?.(charName) || state.players?.[charName] || worldState.players?.[charName] || {};
        const currentArea = state.areas?.[player?.current_area || state.current_area] || null;
        // Build visibility-aware room context affordances for grounding
        const context = this._buildInterpreterContext(charName, state, player, currentArea);
        const interpreted = await interpreter.interpretProseToAction({
            prose,
            charName,
            context,
            directorNote: opts?.directorNote
        });
        if (!interpreted)
            return null;
        // Ground action & target against canonical scene entities
        const grounded = this._groundDirectorDraft(charName, state, player, currentArea, {
            action: interpreted.action || '',
            target: interpreted.target || interpreted.item || null,
            speech: interpreted.speech || null,
            speechVolume: interpreted.speechVolume || 'say',
        }, opts?.scene, opts?.directorNote || '');
        return {
            action: grounded.action,
            item: interpreted.item || null,
            speech: interpreted.speech || null,
            speechVolume: grounded.speechVolume,
            target: grounded.target,
            emote: interpreted.emote || null,
            inner: interpreted.inner_monologue || null,
            inner_monologue: interpreted.inner_monologue || null,
            emotion: interpreted.emotion || null,
            memory: interpreted.memory || null,
            rawProse: interpreted.rawProse
        };
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
            await this._speakLine(charName, player, reply.speech, reply.speechVolume, reply.target, reply.speechTone || reply.tone || null);
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
                            events.logChoices(group.actionWord, group.options, charName);
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
        let llmErrorStopped = false;
        const abortOnLlmError = (phase) => {
            llmErrorStopped = true;
            const detail = phase ? ` (${phase})` : '';
            this.stop(`❌ LLM call failed for ${charName}${detail} - stopping agent`);
            VW?.ui?.setStatus("LLM Error - Stopped", "error");
        };
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
            const memoryNL = typeof PromptBuilder !== 'undefined' && typeof PromptBuilder.buildMemoryContext === 'function'
                ? await PromptBuilder.buildMemoryContext(charName, { report: true })
                : '';
            if (config.reactiveMode) {
                events.logPhase(charName, 'think', 'observing');
                VW?.ui?.setStatus("Thinking...", "info");
                const turnEvents = state.turn_events || [];
                // Threat-aware replan check - before deciding so the plan is fresh.
                // task-185: shouldReplan now returns a REASON string (task-340
                // crisis label) or null; setPlan records the turn clock.
                // task-856: Seed PlanTracker from server active_pursuit if present
                // task-984: Plan generation is an explicit free mental actionWord (`plan [intent]`),
                // not a forced pre-turn LLM call. Seed authored active_pursuit if present and
                // let === YOUR PLAN === cue the agent when no plan is active or replanning is needed.
                PlanTracker.seedFromPlayer?.(charName, player, this.turnNumber);
                const threatAlert = window.ThreatDetector.getThreatAlert(charName, player, currentArea, turnEvents);
                void PlanTracker.shouldReplan(charName, this.turnNumber, threatAlert, player?.vitals);
                if (this._checkCancel())
                    return;
                // ── Multi-action turn (task-352, 2026-10-08) ──
                // A turn holds up to the tier budget (major 1 · minor 1 · free 3).
                // This loops decide→act→react, rebuilding the prompt each pass from
                // fresh state so spent slots hide the actionNames the character can no
                // longer afford (room-context feeds action_points to the brackets;
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
                        if (this._checkCancel())
                            return;
                    }
                    // Phase 2/3 Python Agent Stream (task-1002 / task-1003): prefer
                    // server-side /api/agent/stream (prompt assembly + SSE LLM call in
                    // Python), falling back to /api/agent/prompt + browser LLMClient.
                    let decideHistory = [history[0], { role: 'user', content: '' }];
                    let combinedResponse = null;
                    const usePyStream = agentConfig?.usePythonAgentStream !== false
                        && !threatAlert
                        && typeof ApiClient?.streamAgentPython === 'function';
                    if (usePyStream) {
                        try {
                            const llmCfg = {
                                base_url: agentConfig?.apiUrl || 'http://127.0.0.1:1234/v1',
                                api_key: agentConfig?.apiKey || '',
                                model: agentConfig?.model || '',
                                temperature: Number(agentConfig?.temperature ?? 0.7),
                                max_tokens: Number(agentConfig?.maxTokens ?? 1024),
                                suppress_local_thinking: Boolean(agentConfig?.suppressLocalThinking),
                            };
                            const streamRes = await ApiClient.streamAgentPython({
                                character: charName,
                                phase: 'think',
                                last_result: loopLastResult || '',
                                memory_thought: memoryNL || '',
                                action_points: promptPlayer?.action_points || undefined,
                                execute_side_effects: false,
                                llm: llmCfg,
                            }, (evt) => {
                                if (evt?.type === 'token' && evt.delta && typeof events?.appendStreamChunk === 'function') {
                                    events.appendStreamChunk(charName, 'think-decide', evt.delta);
                                }
                            });
                            if (streamRes && typeof streamRes.raw === 'string' && streamRes.raw.trim()) {
                                combinedResponse = streamRes.raw;
                            }
                        }
                        catch {
                            combinedResponse = null;
                        }
                    }
                    if (combinedResponse === null) {
                        const pyPrompt = await ApiClient.getAgentPrompt?.({
                            character: charName,
                            phase: 'think',
                            last_result: loopLastResult || '',
                            memory_thought: memoryNL || '',
                            action_points: promptPlayer?.action_points || undefined,
                        }).catch(() => null);
                        if (pyPrompt && Array.isArray(pyPrompt.messages) && pyPrompt.messages.length >= 2) {
                            const userContent = threatAlert
                                ? `${threatAlert}\n\n${pyPrompt.messages[1].content}`
                                : pyPrompt.messages[1].content;
                            decideHistory = [
                                pyPrompt.messages[0],
                                { role: 'user', content: userContent },
                            ];
                        }
                        combinedResponse = await this._callLLMMessages(decideHistory, 'think-decide', charName);
                    }
                    // Do NOT replay the assistant output into persistent history.
                    // The react phase uses its own fresh messages; the next turn
                    // restarts with a clean [system, user] context.
                    if (combinedResponse === null) {
                        abortOnLlmError('think/decide phase');
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
                    let { inner, speech: decisionSpeech, speechVolume, speechTone: decisionTone, action: finalAction, emote: decisionEmote, target: decisionTarget } = parsedDecide;
                    this._applyFeltEmotion(charName, parsedDecide.emotion);
                    this._learnNames(charName, parsedDecide.learnedNames);
                    if (inner) {
                        events.logThought(charName, inner);
                        this._persistInnerMonologue(charName, inner, parsedDecide.emotion);
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
                            // malformed payload and an unknown actionWord are ENGINE
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
                        await this._speakLine(charName, player, decisionSpeech, speechVolume, decisionTarget, decisionTone || null);
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
                                if (actionSucceeded && /^(?:plan|replan)(?:\s|$)/i.test(finalAction)) {
                                    const planIntent = finalAction.replace(/^(?:plan|replan)\s*/i, '').trim() || undefined;
                                    const generatedPlan = await window.PlanManager.generate(charName, planIntent);
                                    if (generatedPlan && generatedPlan.length > 0) {
                                        PlanTracker.setPlan(charName, generatedPlan, this.turnNumber);
                                        // Refresh plan state after generation
                                        events.log(`🧠 ${charName} planned: ${generatedPlan.join(' → ')}`, 'msg-thought', {}, charName);
                                        actionResult = `${actionResult ? actionResult + ' ' : ''}Plan formed: ${generatedPlan.join(' → ')}`.trim();
                                    }
                                }
                                PlanTracker.trackStep(charName, finalAction, actionResult, actionSucceeded);
                                let outputText = actionResult;
                                const sysMsgs = Array.isArray(data?.system_messages) ? data.system_messages : [];
                                const narrationUi = agentNarrationUI();
                                const narrationMode = narrationUi?.getMode() || 'none';
                                let narratedText = null;
                                if ((narrationMode === 'ai' && config.apiKey && config.model) || narrationMode === 'player') {
                                    narratedText = await narrationUi.getNarratedActionResult(outputText, charName, finalAction, sysMsgs);
                                }
                                // task-692: preserve mechanical facts alongside narrated prose for the agent prompt
                                const factsSuffix = sysMsgs.length > 0 ? ' ' + sysMsgs.map(m => `(${m})`).join(' ') : '';
                                if (narratedText) {
                                    outputText = narratedText + factsSuffix;
                                }
                                // bug-517: when narration is off, skipped, or fails, preserve the current raw system messages
                                if (!narratedText && sysMsgs.length) {
                                    sysMsgs.forEach((systemMessage) => events.log(systemMessage, 'system-msg'));
                                }
                                agentConfig.lastActionResult[charName] = outputText;
                                // task-340/task-692: pass charName explicitly to msg-narrated so it doesn't default to You
                                if (!outputText.includes('says:')) {
                                    if (narratedText)
                                        events.log(narratedText, 'msg-narrated', {}, charName);
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
                        events.log(`↩️ ${charName}: budget exhausted - auto-substituting "wait"`, 'system-msg');
                        finalAction = 'wait';
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
                    // Dash→go was the original; generalized to actionWord families:
                    // lead → go/approach/release, grab → approach/release.
                    if (finalAction && actionResult && actionSucceeded) {
                        const chainAction = finalAction.split(/\s+/)[0].toLowerCase();
                        const allowed = CHAIN_RULES[chainAction];
                        if (allowed) {
                            actionResult = await this._runChainFollowUp(charName, player, actionResult, history, chainAction, allowed);
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
                            const areaName = freshRoom?.name || freshPlayer?.current_area || freshState?.current_area || '';
                            // task-185: currentArea is the turn-start (pre-action) room -
                            // if it differs from the fresh room the character MOVED this
                            // action, and "surroundings are unchanged" was lying while
                            // pointing the model at a stale observation of the old room.
                            const areaBefore = currentArea?.name || player?.current_area || '';
                            const areaChanged = !movedViaDash && !!areaName && areaName !== areaBefore;
                            const freshAreaKey = freshPlayer?.current_area || freshState?.current_area || '';
                            const preAreaKey = promptPlayer?.current_area || player?.current_area || '';
                            const locationChanged = movedViaDash || areaChanged || (!!freshAreaKey && freshAreaKey !== preAreaKey);
                            const stimulusChanged = Boolean(actionResult && actionResult !== loopLastResult);
                            const reactMemoryNL = (locationChanged || stimulusChanged) && typeof PromptBuilder !== 'undefined' && typeof PromptBuilder.buildMemoryContext === 'function'
                                ? await PromptBuilder.buildMemoryContext(charName, {
                                    preview: true,
                                    area: freshPlayer?.current_area,
                                    stimulus: actionResult,
                                })
                                : memoryNL;
                            const pyReact = await ApiClient.getAgentPrompt?.({
                                character: charName,
                                phase: 'react',
                                what_happened: actionResult || '',
                                memory_thought: reactMemoryNL || '',
                                action_points: freshPlayer?.action_points || undefined,
                                said_this_turn: decisionSpeech || '',
                            }).catch(() => null);
                            const reactMessages = (pyReact && Array.isArray(pyReact.messages) && pyReact.messages.length >= 2)
                                ? [pyReact.messages[0], pyReact.messages[1]]
                                : [{ role: 'system', content: '' }, { role: 'user', content: actionResult || '' }];
                            const reactPrompt = reactMessages[1]?.content || '';
                            let reactResponse = await this._callLLMMessages(reactMessages, 'result-reaction', charName);
                            if (reactResponse === null) {
                                abortOnLlmError('reaction phase');
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
                            const { inner: reactionInner, speech: reactionSpeech, speechVolume: reactionVolume, speechTone: reactionTone, emote: reactionEmote } = parsedReact;
                            if (reactionInner) {
                                events.logThought(charName, reactionInner);
                                this._persistInnerMonologue(charName, reactionInner, parsedReact.emotion);
                            }
                            this._applyFeltEmotion(charName, parsedReact.emotion);
                            this._learnNames(charName, parsedReact.learnedNames);
                            if (reactionSpeech) {
                                await this._speakLine(charName, player, reactionSpeech, reactionVolume, null, reactionTone || null);
                            }
                            if (reactionEmote) {
                                await this._performEmote(charName, reactionEmote);
                            }
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
                        const slotsNow = (worldState.data?.players?.[charName]?.action_points);
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
                const pyCombined = await ApiClient.getAgentPrompt?.({
                    character: charName,
                    phase: 'think',
                    last_result: lastResult || '',
                    memory_thought: memoryNL || '',
                    action_points: player?.action_points || undefined,
                }).catch(() => null);
                const combinedHistory = (pyCombined && Array.isArray(pyCombined.messages) && pyCombined.messages.length >= 2)
                    ? [pyCombined.messages[0], pyCombined.messages[1]]
                    : [history[0], { role: 'user', content: lastResult || '' }];
                let reactionResponse = await this._callLLMMessages(combinedHistory, 'combined', charName);
                if (reactionResponse === null) {
                    abortOnLlmError();
                    return;
                }
                let parsedNonReactive = ResponseParser.parseReaction(reactionResponse) ?? { inner: '', speech: null, speechVolume: 'say', action: '', emote: null, memory: null, emotion: null, parseError: null };
                if (parsedNonReactive.parseError) {
                    events.logParseError(charName, 'combined', parsedNonReactive.parseError, reactionResponse);
                }
                let { inner, speech, speechVolume, speechTone, action, emote: reactionEmote, target: speechTarget } = parsedNonReactive;
                if (inner) {
                    events.log(`[${player.name} inner] ${inner}`, "msg-thought");
                    this._persistInnerMonologue(charName, inner, parsedNonReactive.emotion);
                }
                this._applyFeltEmotion(charName, parsedNonReactive.emotion);
                this._learnNames(charName, parsedNonReactive.learnedNames);
                if (speech) {
                    await this._speakLine(charName, player, speech, speechVolume, speechTarget, speechTone || null);
                }
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
            if (!llmErrorStopped) {
                VW?.ui?.setStatus(config.running ? "Waiting..." : "Idle.", "info");
            }
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
                if (!config.running)
                    break;
                if (this._paused)
                    continue;
                // Async mode counts completed character turns, not idle scheduler
                // polls. A 5-120 second cooldown must not hit the max-step limit
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
        this._recentInnerMonologues = {};
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
     * unknown actionWord is an engine-side refusal, and saying "you try to X, but
     * you can't do that" made characters invent supernatural barriers to
     * explain a malformed JSON payload. The character is told what actually
     * happened: the command never reached the world.
     *
     * @param {string} charName - Character name
     * @param {string} rejectedAction - The rejected action text
     * @param {string} category - 'schema_invalid' | 'unknown_action' | 'empty'
     */
    _surfaceRejectedAction(charName, rejectedAction, category = 'unknown_action') {
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
     * @param {string} failedAction - The action string that failed ('' if actionWord-rejected)
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
        const prompt = `Your previous action "${attempted}" failed: ${failedResult}\nChoose a different valid action you can afford right now. Respond with ONLY raw JSON.`;
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
     * immediate decision to continue with an allowed actionWord (go/approach/
     * release/wait). Returns the combined result text.
     */
    async _runChainFollowUp(charName, player, resultText, history, sourceAction, allowedActions) {
        await worldState.fetch();
        const freshState = worldState.data;
        if (!freshState)
            return resultText;
        const freshPlayer = freshState?.players?.[charName] || player;
        const currentArea = freshState.areas?.[freshPlayer?.current_area || freshState.current_area] || null;
        events.logPhase(charName, 'decide', `${sourceAction} follow-up`);
        VW?.ui?.setStatus?.("Chain follow-up...", "info");
        const prompt = `Your "${sourceAction}" succeeded: ${resultText}\nYou may immediately follow up with one of: ${allowedActions.join(', ')}. Respond with ONLY raw JSON.`;
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
        const actionWord = followAction.split(/\s+/)[0].toLowerCase();
        const exitNames = Object.keys(currentArea?.exits || {}).map(e => e.toLowerCase());
        const allowed = allowedActions.includes(actionWord);
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
            events.log(`${sourceAction} follow-up error: ${err instanceof Error ? err.message : String(err)}`, 'error-msg');
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
            history.push({ role: 'user', content: 'Your previous reply was rejected: the "action" field must be a single actionWord string (for example "action": "take"), never an object and never a sentence. Respond again with the same schema, with "action" as a plain actionWord string.' });
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
        if (stepName === 'result-reaction' || stepName === 'director-react')
            return F.agentReact;
        if (stepName === 'think-decide' || stepName === 'director-draft' || stepName === 'combined' || stepName === 'auto-retry' || stepName === 'chain-follow-up')
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
