/**
 * tools/unit/test_turn_prompts.js - prompt surfacing of dice/skill checks
 * (task-479).
 *
 * `summaryLine` condenses a previous action result into the one-line RECENTLY
 * block. Before task-479 it took the first line only, so a check result that
 * was not the first line (a trigger appends its outputs, a movement prepends a
 * pass message) never reached the model, and the narration had no roll to
 * explain. These pin the behaviour.
 */
'use strict';

const promptBuilder479 = window.PromptBuilder;

test('summaryLine returns the first line when no check is present', () => {
    assertEq(promptBuilder479.summaryLine('You climb the wall.\nThe wind bites.'), 'You climb the wall.');
});

test('summaryLine keeps a check line that is the first line', () => {
    const text = '[Skill Check] Athletics vs DC 15 (medium): roll=12 + 3 = 15 => success\nYou haul yourself over.';
    assertEq(promptBuilder479.summaryLine(text),
        '[Skill Check] Athletics vs DC 15 (medium): roll=12 + 3 = 15 => success');
});

test('summaryLine surfaces a check line that is NOT the first line', () => {
    const text = 'You search the debris.\n[Skill Check] Investigation vs DC 12 (medium): roll=18 + 2 = 20 => success';
    assertEq(promptBuilder479.summaryLine(text),
        '[Skill Check] Investigation vs DC 12 (medium): roll=18 + 2 = 20 => success - You search the debris.');
});

test('summaryLine recognises saves, generic checks and grabs', () => {
    assertEq(promptBuilder479.summaryLine('nothing happened\n[Save] DEX vs DC 12: roll 4 + 1 = 5 => failure'),
        '[Save] DEX vs DC 12: roll 4 + 1 = 5 => failure - nothing happened');
    assertEq(promptBuilder479.summaryLine('nothing happened\n[Check] attack vs DC 5 (very easy): roll=9 + 2 = 11 => success'),
        '[Check] attack vs DC 5 (very easy): roll=9 + 2 = 11 => success - nothing happened');
    assertEq(promptBuilder479.summaryLine('nothing happened\n[Grab] Athletics vs DC 14: roll 10 + 6 = 16 => success'),
        '[Grab] Athletics vs DC 14: roll 10 + 6 = 16 => success - nothing happened');
});

test('summaryLine on empty text is empty', () => {
    assertEq(promptBuilder479.summaryLine(''), '');
    assertEq(promptBuilder479.summaryLine(null), '');
});

test('bug-517: room-context.ts does not call playerSpeak', () => {
    const src = __readFile('static/js/agent/prompt-builder/room-context.ts');
    assertEq(src.includes('playerSpeak'), false, 'room-context must not invoke playerSpeak');
});

test('bug-559: available actions prompt block omits major verbs when major budget is 0', () => {
    const pb = window.PromptBuilder;
    const state = {
        players: {},
        players_in_area: [{ name: 'Belne', description: 'goblin' }]
    };
    const player = { name: 'Arix', vitals: { Energy: 80, Bladder: 10 } };
    const area = { name: 'Food Storage', ambient_light: 50, exits: {} };
    
    // With full budget: attack is present
    const fullBlock = pb.buildAvailableActionsBlock(state, 'Arix', player, area, { major: 1, minor: 1, free: 3, activity: 1 });
    assertTrue(fullBlock.includes('attack  -  fight'), 'Full budget should have attack');

    // With major: 0: attack is omitted, note is present
    const spentMajorBlock = pb.buildAvailableActionsBlock(state, 'Arix', player, area, { major: 0, minor: 1, free: 3, activity: 1 });
    assertFalse(spentMajorBlock.includes('attack  -  fight'), 'Exhausted major budget should omit attack');
    assertTrue(spentMajorBlock.includes('Major actions exhausted this turn'), 'Should explain major actions exhausted');
    assertTrue(spentMajorBlock.includes('grab  -  seize'), 'Minor action grab should remain');

    // With major: 0 and minor: 0: grab omitted, exhausted both note present
    const spentBothBlock = pb.buildAvailableActionsBlock(state, 'Arix', player, area, { major: 0, minor: 0, free: 3, activity: 1 });
    assertFalse(spentBothBlock.includes('grab  -  seize'), 'Exhausted minor budget should omit grab');
    assertTrue(spentBothBlock.includes('Major and minor actions exhausted this turn'), 'Should explain both exhausted');
    assertTrue(spentBothBlock.includes('wait  -  wait or hold still'), 'Wait should remain');
});

test('buildAvailableActionsBlock surfaces phone verbs only for active phone and call state (bug-599)', () => {
    const pb = window.PromptBuilder;
    const savedGraph = worldState.graph;
    const savedGetNode = worldState.getNode;
    const savedGetNodeById = worldState.getNodeByIdentifier;
    try {
        const nodes = {
            player_Arix: { id: 'player_Arix', type: 'player', name: 'Arix', properties: {} },
            phone_1: { id: 'phone_1', type: 'item', name: 'smartphone', properties: { tags: ['device', 'phone'], uses: 0 } },
        };
        worldState.graph = {
            edges: [{ source: 'phone_1', target: 'player_Arix', type: 'carrying' }],
        };
        worldState.getNode = (id) => nodes[id] || null;
        worldState.getNodeByIdentifier = () => null;

        const state = { players_in_area: [{ name: 'Arix' }], players: {} };
        const area = { name: 'Dorm', ambient_light: 50, exits: {} };

        // Dead phone (uses: 0): no call/text/answer/hangup
        const deadBlock = pb.buildAvailableActionsBlock(state, 'Arix', { name: 'Arix', vitals: {} }, area);
        assertFalse(deadBlock.includes('call  -  '), 'Dead phone should not surface call');
        assertFalse(deadBlock.includes('text  -  '), 'Dead phone should not surface text');

        // Active phone with incoming call: call, text, answer, hangup
        nodes.phone_1.properties.uses = 5;
        const ringingBlock = pb.buildAvailableActionsBlock(state, 'Arix', {
            name: 'Arix',
            vitals: {},
            incoming_call_from: 'Buffy',
        }, area);
        assertTrue(ringingBlock.includes('call  -  '), 'Active phone should surface call');
        assertTrue(ringingBlock.includes('text  -  '), 'Active phone should surface text');
        assertTrue(ringingBlock.includes('answer  -  answer incoming call from Buffy'), 'Incoming call should surface answer');
        assertTrue(ringingBlock.includes('hangup  -  dismiss incoming call from Buffy'), 'Incoming call should surface hangup');

        // Active phone on_a_call: hangup surfaced, answer omitted
        const onCallBlock = pb.buildAvailableActionsBlock(state, 'Arix', {
            name: 'Arix',
            vitals: {},
            conditions: { on_a_call: true },
        }, area);
        assertTrue(onCallBlock.includes('hangup  -  end the current phone call'), 'On a call should surface hangup');
        assertFalse(onCallBlock.includes('answer  -  '), 'On a call should not surface answer');
    } finally {
        worldState.graph = savedGraph;
        worldState.getNode = savedGetNode;
        worldState.getNodeByIdentifier = savedGetNodeById;
    }
});

test('bug-606: buildResultReactionPrompt examples use canonical emotion array shape without emotion:null', () => {
    const pb = window.PromptBuilder;
    const prompt = pb.buildResultReactionPrompt(
        'Arix',
        { name: 'Arix', vitals: { Energy: 80 } },
        '[Tick 1] You are still in Dorm.',
        'Energy 80%',
        'calm',
        '',
        'Check the door.',
        'examine door',
        'The door is locked.',
        '',
        ''
    );
    assertFalse(prompt.includes('"emotion":null'), 'buildResultReactionPrompt must not emit legacy "emotion":null');

    const emoteLine = prompt.split('\n').find(l => l.includes('"emote":"..."') && l.includes('"speech":null'));
    const noopLine = prompt.split('\n').find(l => l.includes('"emote":null') && l.includes('"speech":null'));
    assertTrue(!!emoteLine, 'Silent emote example line present');
    assertTrue(!!noopLine, 'Noop example line present');

    const emoteObj = JSON.parse(emoteLine.trim());
    const noopObj = JSON.parse(noopLine.trim());
    assertTrue(Array.isArray(emoteObj.emotion), 'Silent emote example uses array emotion');
    assertTrue(Array.isArray(noopObj.emotion), 'Noop example uses array emotion');
    assertEq(noopObj.emotion.length, 0, 'Noop example uses empty emotion array');
});

test('bug-606: AgentEngine refreshes vitals, emotion, relationship, and read-only memory snapshots for react phase', async () => {
    const saved = {
        agent: window.agent,
        fetch: window.fetch,
        RateLimiter: window.RateLimiter,
        worldState: window.worldState,
        agentApi: window.agentApi,
        agentConfig: window.agentConfig,
        config: window.config,
        events: window.events,
        PromptBuilder: window.PromptBuilder,
        ResponseParser: window.ResponseParser,
        PlanTracker: window.PlanTracker,
        AgentState: window.AgentState,
        AgentMemory: window.AgentMemory,
        ThreatDetector: window.ThreatDetector,
        ActionNormalizer: window.ActionNormalizer,
    };
    window.RateLimiter = window.RateLimiter || class {};
    window.config = {
        apiKey: 'test-key',
        model: 'test-model',
        controllingPlayer: 'Arix',
        reactiveMode: true,
        running: true,
        busy: false,
        autoRetryInvalid: false,
        lastActionResult: {},
        lastRoom: {},
        charTurnCounts: {},
    };
    const savedSetActivePlayer = ApiClient.setActivePlayer;
    const savedAction = ApiClient.action;
    let phaseIndex = 0;
    ApiClient.setActivePlayer = async () => {};
    ApiClient.action = async () => {
        phaseIndex = 1;
        return { output: 'You slip into the Kitchen and trip on a crate.', success: true, system_messages: [] };
    };
    const AgentEngineCtor = new Function(window.__readFile('static/js/agent-engine.js') + '; return AgentEngine;')();
    window.agent = saved.agent;

    try {
        const prePlayer = {
            name: 'Arix',
            current_area: 'Foyer',
            vitals: { Energy: 90 },
            emotion: { label: 'calm', intensity: 2 },
            relationships: { Guard: { closeness: 1 } },
        };
        const postPlayer = {
            name: 'Arix',
            current_area: 'Kitchen',
            vitals: { Energy: 35 },
            emotion: { label: 'alarmed', intensity: 8 },
            relationships: { Guard: { closeness: -5 } },
            turn_slots: { major: 0, minor: 0, free: 0 },
        };
        const preState = {
            current_area: 'Foyer',
            time_ticks: 1,
            players: { Arix: prePlayer },
            areas: {
                Foyer: { name: 'Foyer', exits: { north: 'Kitchen' } },
                Kitchen: { name: 'Kitchen', exits: { south: 'Foyer' } },
            },
            turn_events: [],
        };
        const postState = {
            current_area: 'Kitchen',
            time_ticks: 2,
            players: { Arix: postPlayer },
            areas: {
                Foyer: { name: 'Foyer', exits: { north: 'Kitchen' } },
                Kitchen: { name: 'Kitchen', exits: { south: 'Foyer' } },
            },
            turn_events: [],
        };

        window.worldState = {
            data: preState,
            players: preState.players,
            setRuntimeFocusForCharacter: () => {},
            fetch: async () => {
                const next = phaseIndex === 0 ? preState : postState;
                window.worldState.data = next;
                window.worldState.players = next.players;
            },
        };
        window.fetch = async () => ({ ok: true, json: async () => ({}) });
        window.agentConfig = window.config;
        const logs = [];
        window.events = {
            isAutonomous: () => true,
            log: (msg, cls) => { logs.push({ msg, cls }); },
            logPhase: () => {},
            logThought: () => {},
            logParseError: () => {},
            trackAction: () => {},
            trackPhase: () => {},
        };
        window.AgentState = {
            isBusy: () => false,
            clearUnconscious: () => null,
        };
        window.AgentMemory = {
            reflect: async () => {},
            storeMemory: () => {},
        };
        window.ThreatDetector = {
            getThreatAlert: () => '',
        };
        window.PlanTracker = {
            seedFromPlayer: () => {},
            shouldReplan: () => null,
            trackStep: () => {},
            buildPlanContext: () => '',
        };
        window.ActionNormalizer = {
            classifyAction: () => ({ ok: true }),
        };

        const memoryCalls = [];
        const reactPromptCalls = [];
        window.PromptBuilder = Object.assign({}, saved.PromptBuilder, {
            buildRoomContextParts: (_s, _c, p, area) => ({ area: area?.name || p?.current_area || '' }),
            describeVitals: (p) => `Energy=${p?.vitals?.Energy}`,
            buildEmotionContext: (p) => `Emotion=${p?.emotion?.label}`,
            buildRelationshipContext: (p) => `RelGuard=${p?.relationships?.Guard?.closeness}`,
            buildMemoryContext: async (_c, opts) => {
                memoryCalls.push(opts || {});
                return opts?.preview ? `MEM_PREVIEW_${opts.area}` : 'MEM_TURN_START';
            },
            buildPlanContext: () => '',
            buildReactionPrompt: () => 'DECIDE_PROMPT',
            buildReactSystemPrompt: () => 'REACT_SYSTEM',
            buildResultReactionPrompt: (charName, playerArg, reactContext, vitalsNL, emotionNL, relationshipNL, _inner, _action, _result, memoryNL) => {
                reactPromptCalls.push({
                    charName,
                    area: playerArg?.current_area,
                    reactContext,
                    vitalsNL,
                    emotionNL,
                    relationshipNL,
                    memoryNL,
                });
                return 'REACT_PROMPT';
            },
        });
        window.ResponseParser = {
            parseReaction: () => ({ inner: 'Move north.', speech: null, speechVolume: 'say', action: 'go north', emote: null, memory: null, emotion: null, parseError: null }),
            parseResultReaction: () => ({ inner: 'Ouch.', speech: null, speechVolume: 'say', emote: null, memory: null, emotion: null, parseError: null }),
        };

        const engine = new AgentEngineCtor();
        engine.characterHistories = {};
        engine.turnQueue = [];
        engine._rateLimiter = { waitMs: () => 0, msUntilAvailable: () => 0, isRateLimited: () => false };
        engine.getHistory = (name) => (engine.characterHistories[name] = engine.characterHistories[name] || [{ role: 'system', content: 'SYS' }]);
        engine._checkCancel = () => false;
        engine._applyFeltEmotion = () => {};
        engine._learnNames = () => {};
        engine._persistInnerMonologue = () => {};
        engine._isNoopAction = () => false;
        engine._endTurnEarly = () => {};
        engine._callLLMMessages = async (_msgs, stepName) => {
            if (stepName === 'think-decide') return '{"inner_monologue":"Move north.","action":"go north"}';
            return '{"inner_monologue":"Ouch.","speech":null,"volume":null,"emote":null,"emotion":[],"learned_names":[]}';
        };

        await engine.step();

        assertEq(reactPromptCalls.length, 1, 'buildResultReactionPrompt called once (logs: ' + JSON.stringify(logs) + ')');
        const call = reactPromptCalls[0];
        assertEq(call.area, 'Kitchen', 'freshPlayer passed to buildResultReactionPrompt');
        assertEq(call.vitalsNL, 'Energy=35', 'post-action vitalsNL refreshed');
        assertEq(call.emotionNL, 'Emotion=alarmed', 'post-action emotionNL refreshed');
        assertEq(call.relationshipNL, 'RelGuard=-5', 'post-action relationshipNL refreshed');
        assertEq(call.memoryNL, 'MEM_PREVIEW_Kitchen', 'post-action memoryNL refreshed read-only');

        const previewCall = memoryCalls.find(c => c.preview === true);
        assertTrue(!!previewCall, 'buildMemoryContext called with preview: true');
        assertEq(previewCall.area, 'Kitchen', 'preview memory refresh targets freshPlayer.current_area');
    } finally {
        ApiClient.setActivePlayer = savedSetActivePlayer;
        ApiClient.action = savedAction;
        Object.assign(window, saved);
    }
});
