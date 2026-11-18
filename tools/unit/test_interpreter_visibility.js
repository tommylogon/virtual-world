/**
 * test_interpreter_visibility.js
 *
 * Verifies AgentEngine._buildInterpreterContext, interpretProseToDraft, and
 * draftTurnForCharacter never leak hidden items, hidden characters, or unmet
 * stranger real names into ActionInterpreter prompts (bug-597).
 */

function makeAgentEngineInstance() {
    const prevAgent = window.agent;
    window.RateLimiter = window.RateLimiter || class {};
    const AgentEngineCtor = new Function(window.__readFile('static/js/agent-engine.js') + '; return AgentEngine;')();
    window.agent = prevAgent;
    return Object.create(AgentEngineCtor.prototype);
}

function withMockWorldState(data, itemsByArea, fn) {
    const prevWorldState = window.worldState;
    try {
        window.worldState = {
            data,
            runtimeData: data,
            runtimePlayer: (name) => data.players?.[name] || null,
            getItemsInArea: (areaName) => itemsByArea[areaName] || [],
            hasMet: (viewer, target) => Array.isArray(data.players?.[viewer]?.met) && data.players[viewer].met.includes(target),
        };
        return fn();
    } finally {
        window.worldState = prevWorldState;
    }
}

test('_buildInterpreterContext filters hidden items and respects dim/pitch_black light rules', () => {
    const eng = makeAgentEngineInstance();
    const itemsByArea = {
        Cellar: [
            { id: 'item_crate', name: 'heavy wooden crate', properties: { weight: 20, current_state: 'idle' } },
            { id: 'item_key', name: 'brass key', properties: { weight: 1, current_state: 'idle' } },
            { id: 'item_trapdoor', name: 'secret trapdoor', properties: { weight: 15, current_state: 'hidden' } },
        ],
    };

    const makeState = (light) => ({
        current_area: 'Cellar',
        areas: {
            Cellar: {
                name: 'Cellar',
                ambient_light: light,
                ways: { North: { to: 'Hallway', direction: 'north' } },
            },
        },
        players: {
            Alice: { current_area: 'Cellar', met: [], known: [], inventory: { flashlight: {} } },
        },
        players_in_area: [],
    });

    // Normal light (50): non-hidden items visible, hidden item excluded
    withMockWorldState(makeState(50), itemsByArea, () => {
        const state = window.worldState.data;
        const ctx = eng._buildInterpreterContext('Alice', state, state.players.Alice, state.areas.Cellar);
        assertTrue(ctx.thingsVisible.includes('heavy wooden crate'), 'Normal light shows crate');
        assertTrue(ctx.thingsVisible.includes('brass key'), 'Normal light shows small key');
        assertFalse(ctx.thingsVisible.includes('secret trapdoor'), 'Hidden item never visible in normal light');
    });

    // Dim light (30): only heavy items (weight >= 3) visible
    withMockWorldState(makeState(30), itemsByArea, () => {
        const state = window.worldState.data;
        const ctx = eng._buildInterpreterContext('Alice', state, state.players.Alice, state.areas.Cellar);
        assertTrue(ctx.thingsVisible.includes('heavy wooden crate'), 'Dim light shows heavy crate');
        assertFalse(ctx.thingsVisible.includes('brass key'), 'Dim light hides small key');
        assertFalse(ctx.thingsVisible.includes('secret trapdoor'), 'Hidden item excluded in dim light');
    });

    // Pitch black (10): no items visible without dark_vision
    withMockWorldState(makeState(10), itemsByArea, () => {
        const state = window.worldState.data;
        const ctx = eng._buildInterpreterContext('Alice', state, state.players.Alice, state.areas.Cellar);
        assertEq(ctx.thingsVisible.length, 0, 'Pitch black hides all items');
    });

    // Pitch black with dark_vision: non-hidden items visible, hidden still excluded
    const dvState = makeState(10);
    dvState.players.Alice.traits = { dark_vision: true };
    withMockWorldState(dvState, itemsByArea, () => {
        const state = window.worldState.data;
        const ctx = eng._buildInterpreterContext('Alice', state, state.players.Alice, state.areas.Cellar);
        assertTrue(ctx.thingsVisible.includes('heavy wooden crate'), 'Dark vision sees crate in pitch black');
        assertTrue(ctx.thingsVisible.includes('brass key'), 'Dark vision sees key in pitch black');
        assertFalse(ctx.thingsVisible.includes('secret trapdoor'), 'Dark vision still excludes hidden item');
    });
});

test('_buildInterpreterContext masks unmet strangers and excludes hidden characters', () => {
    const eng = makeAgentEngineInstance();
    const state = {
        current_area: 'Lobby',
        areas: {
            Lobby: { name: 'Lobby', ambient_light: 60, ways: {} },
        },
        players: {
            Alice: { current_area: 'Lobby', met: ['Bob'], known: [], inventory: {} },
            Bob: { current_area: 'Lobby', description: 'A cheerful clerk in a blue vest.', tags: ['male'] },
            MarcusVance: { current_area: 'Lobby', description: 'A tall man in a torn trench coat. He looks exhausted.', tags: ['male'] },
            ShadowStalker: { current_area: 'Lobby', description: 'A crouched figure.', hidden: true },
        },
        players_in_area: [
            { name: 'Bob', state: 'awake', description: 'A cheerful clerk in a blue vest.' },
            { name: 'MarcusVance', state: 'awake', description: 'A tall man in a torn trench coat. He looks exhausted.' },
            { name: 'ShadowStalker', state: 'awake', description: 'A crouched figure.', hidden: true },
        ],
    };

    withMockWorldState(state, { Lobby: [] }, () => {
        const ctx = eng._buildInterpreterContext('Alice', state, state.players.Alice, state.areas.Lobby);
        assertTrue(ctx.peopleHere.includes('Bob'), 'Met character keeps real name');
        assertFalse(ctx.peopleHere.some((p) => p.includes('MarcusVance')), 'Unmet stranger real name must not appear');
        assertFalse(ctx.peopleHere.some((p) => p.includes('ShadowStalker')), 'Hidden character must be excluded');
        assertEq(ctx.peopleHere.length, 2, 'Only Bob and masked MarcusVance should be in peopleHere');
    });
});

test('interpretProseToDraft and draftTurnForCharacter never leak hidden or unmet names to ActionInterpreter prompts', async () => {
    const eng = makeAgentEngineInstance();
    const prevConfig = window.config;
    const prevActionInterpreter = window.ActionInterpreter;
    const prevWorldState = window.worldState;
    const prevBuildDecidePrompt = window.PromptBuilder?.buildDecidePrompt;
    const prevBuildMemoryContext = window.PromptBuilder?.buildMemoryContext;

    const capturedPrompts = [];
    const state = {
        current_area: 'Alley',
        areas: {
            Alley: {
                name: 'Alley',
                ambient_light: 55,
                ways: { Street: { to: 'Main Street', direction: 'east' } },
            },
        },
        players: {
            Alice: {
                current_area: 'Alley',
                met: [],
                known: [],
                inventory: {},
                traits: {},
                conditions: {},
                vitals: { health: 100 },
            },
            SecretKiller: {
                current_area: 'Alley',
                description: 'A broad-shouldered figure in a rain poncho.',
                tags: ['male'],
            },
            HiddenWatcher: {
                current_area: 'Alley',
                description: 'Someone hiding behind the dumpster.',
                hidden: true,
            },
        },
        players_in_area: [
            { name: 'SecretKiller', state: 'awake', description: 'A broad-shouldered figure in a rain poncho.' },
            { name: 'HiddenWatcher', state: 'awake', description: 'Someone hiding behind the dumpster.', hidden: true },
        ],
    };
    const itemsByArea = {
        Alley: [
            { id: 'i_dumpster', name: 'rusted dumpster', properties: { weight: 100, current_state: 'idle' } },
            { id: 'i_knife', name: 'hidden bloodstained knife', properties: { weight: 1, current_state: 'hidden' } },
        ],
    };

    try {
        window.worldState = {
            data: state,
            runtimeData: state,
            runtimePlayer: (name) => state.players?.[name] || null,
            getItemsInArea: (areaName) => itemsByArea[areaName] || [],
            hasMet: (viewer, target) => Array.isArray(state.players?.[viewer]?.met) && state.players[viewer].met.includes(target),
            fetch: async () => state,
        };
        if (window.PromptBuilder) {
            window.PromptBuilder.buildDecidePrompt = (_c, ctx) => ctx;
            window.PromptBuilder.buildMemoryContext = async () => '';
        }
        window.config = {
            apiKey: 'test-key',
            model: 'test-model',
            interpreterModelEnabled: true,
        };
        window.ActionInterpreter = {
            async interpretProseToAction(params) {
                const built = prevActionInterpreter.buildExtractionPrompt(params);
                capturedPrompts.push(built.userPrompt);
                return {
                    action: null,
                    item: null,
                    target: null,
                    speech: 'Who is there?',
                    speechVolume: 'say',
                    emote: 'squints into the alley',
                    inner_monologue: 'Someone is here.',
                    emotion: 'uneasy',
                    memory: null,
                    rawProse: params.prose,
                };
            },
        };

        // 1. Test interpretProseToDraft
        await eng.interpretProseToDraft('Alice', 'Alice squints into the alley. "Who is there?"');

        // 2. Test draftTurnForCharacter (director compose path)
        eng.buildSystemPrompt = () => 'system';
        eng.buildContextPrompt = () => 'context';
        eng._injectDirectorSteering = (p) => p;
        eng.callLLM = async () => 'Alice steps back and asks, "Who is there?"';

        await eng.draftTurnForCharacter('Alice', { phase: 'compose', directorNote: '' });

        assertEq(capturedPrompts.length, 2, 'Both interpretProseToDraft and draftTurnForCharacter invoked ActionInterpreter');
        for (const promptText of capturedPrompts) {
            assertTrue(promptText.includes('rusted dumpster'), 'Visible item appears in prompt');
            assertFalse(promptText.includes('hidden bloodstained knife'), 'Hidden item must not leak into prompt');
            assertFalse(promptText.includes('SecretKiller'), 'Unmet stranger real name must not leak into prompt');
            assertFalse(promptText.includes('HiddenWatcher'), 'Hidden character must not leak into prompt');
        }
    } finally {
        if (window.PromptBuilder) {
            window.PromptBuilder.buildDecidePrompt = prevBuildDecidePrompt;
            window.PromptBuilder.buildMemoryContext = prevBuildMemoryContext;
        }
        window.config = prevConfig;
        window.ActionInterpreter = prevActionInterpreter;
        window.worldState = prevWorldState;
    }
});
