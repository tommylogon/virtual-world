/**
 * bug-589 - StructuredFormats.plan strict schema and PlanManager/PlanGrounding
 * typed-step contract end-to-end tests.
 */

test('StructuredFormats.plan defines strict typed step object schema', () => {
    const fmt = StructuredFormats.plan;
    assertTrue(Boolean(fmt), 'StructuredFormats.plan exists');
    assertEq(fmt.type, 'json_schema', 'plan format type');
    assertEq(fmt.json_schema.name, 'plan', 'plan schema name');
    assertEq(fmt.json_schema.strict, true, 'plan schema strict mode');

    const root = fmt.json_schema.schema;
    assertEq(root.type, 'object', 'root must be object');
    assertEq(root.additionalProperties, false, 'root must disallow additionalProperties');
    assertEq(JSON.stringify(root.required), JSON.stringify(['steps']), 'root requires steps');

    const stepsProp = root.properties.steps;
    assertEq(stepsProp.type, 'array', 'steps must be array');

    const itemSchema = stepsProp.items;
    assertEq(itemSchema.type, 'object', 'steps.items must be object');
    assertEq(itemSchema.additionalProperties, false, 'steps.items must disallow additionalProperties');

    const expectedFields = ['action', 'item', 'target', 'text', 'note', 'area', 'until', 'duration'];
    assertEq(
        JSON.stringify(itemSchema.required),
        JSON.stringify(expectedFields),
        'steps.items.required lists every typed step property',
    );
    assertEq(itemSchema.properties.action.type, 'string', 'action is required string');
    for (const field of ['item', 'target', 'text', 'note', 'area', 'until']) {
        assertEq(
            JSON.stringify(itemSchema.properties[field].type),
            JSON.stringify(['string', 'null']),
            `${field} is nullable string`,
        );
    }
    assertEq(
        JSON.stringify(itemSchema.properties.duration.type),
        JSON.stringify(['number', 'null']),
        'duration is nullable number',
    );
});

async function withPlanManagerEnv(fn) {
    const saved = {
        apiKey: config.apiKey,
        apiBase: config.apiBase,
        model: config.model,
        lastActionResult: config.lastActionResult,
        worldData: worldState.data,
        getNode: worldState.getNode,
        getItemsInArea: worldState.getItemsInArea,
        graph: worldState.graph,
        PromptBuilder: globalThis.PromptBuilder,
        events: globalThis.events,
        PlanTracker: globalThis.PlanTracker,
        llmClient: globalThis.llmClient,
        PlanGrounding: window.PlanGrounding,
    };

    config.apiKey = 'test-key';
    config.apiBase = 'https://api.example.com/v1';
    config.model = 'test-model';
    config.lastActionResult = {};

    worldState.data = {
        players: {
            Rikka: {
                current_area: 'Camp',
                inventory: [],
                known: ['Camp'],
                vitals: {},
            },
        },
        players_in_area: [{ name: 'Rikka' }],
        areas: {
            Camp: {
                name: 'Camp',
                items: ['dried meat'],
                exits: {
                    west: { direction: 'west', label: 'west passage' },
                },
            },
        },
    };
    worldState.getNode = () => null;
    worldState.getItemsInArea = () => [{ id: 'item_meat', name: 'dried meat' }];
    worldState.graph = { edges: [] };

    globalThis.PromptBuilder = {
        buildRoomContext: () => 'Room: Camp',
        describeVitals: () => '',
        buildEmotionContext: () => '',
        buildMemoryContext: async () => '',
    };
    globalThis.events = {
        getCharacterState: () => ({ lastThought: '' }),
        log: () => {},
    };
    globalThis.PlanTracker = {
        criticalNeeds: () => [],
        getPlan: () => [],
        getProgress: () => 0,
        getFailures: () => [],
    };

    try {
        await fn();
    } finally {
        config.apiKey = saved.apiKey;
        config.apiBase = saved.apiBase;
        config.model = saved.model;
        config.lastActionResult = saved.lastActionResult;
        worldState.data = saved.worldData;
        worldState.getNode = saved.getNode;
        worldState.getItemsInArea = saved.getItemsInArea;
        worldState.graph = saved.graph;
        globalThis.PromptBuilder = saved.PromptBuilder;
        globalThis.events = saved.events;
        globalThis.PlanTracker = saved.PlanTracker;
        globalThis.llmClient = saved.llmClient;
        window.PlanGrounding = saved.PlanGrounding;
    }
}

test('PlanManager.generate sends StructuredFormats.plan and grounds strict typed steps with nulls', async () => {
    await withPlanManagerEnv(async () => {
        let capturedOpts = null;
        globalThis.llmClient = {
            chat: async (_messages, opts) => {
                capturedOpts = opts;
                return JSON.stringify({
                    steps: [
                        {
                            action: 'take',
                            item: 'dried meat',
                            target: null,
                            text: null,
                            note: null,
                            area: null,
                            until: null,
                            duration: null,
                        },
                        {
                            action: 'go',
                            item: null,
                            target: 'west passage',
                            text: null,
                            note: null,
                            area: null,
                            until: null,
                            duration: null,
                        },
                        {
                            action: 'perform',
                            item: null,
                            target: null,
                            text: null,
                            note: 'cook meat',
                            area: null,
                            until: 'done',
                            duration: 15,
                        },
                    ],
                });
            },
        };

        const steps = await PlanManager.generate('Rikka');
        assertEq(capturedOpts.responseFormat, StructuredFormats.plan, 'passes StructuredFormats.plan');
        assertEq(steps.length, 3, 'returns 3 grounded steps');
        assertEq(steps[0], 'take dried meat', 'first step grounded and rendered');
        assertEq(steps[1], 'go west passage', 'second step grounded and rendered');
        assertEq(steps[2], 'perform: cook meat until done', 'perform step grounded and rendered');
    });
});

test('PlanManager.generate keeps graceful fallback for legacy string plans', async () => {
    await withPlanManagerEnv(async () => {
        globalThis.llmClient = {
            chat: async () => JSON.stringify({
                steps: ['take dried meat', 'go west passage'],
            }),
        };

        const steps = await PlanManager.generate('Rikka');
        assertEq(steps.length, 2, 'returns legacy string steps');
        assertEq(steps[0], 'take dried meat', 'preserves first legacy step');
        assertEq(steps[1], 'go west passage', 'preserves second legacy step');
    });
});

test('PlanManager.generate formats strict typed steps when PlanGrounding is unavailable', async () => {
    await withPlanManagerEnv(async () => {
        window.PlanGrounding = undefined;
        globalThis.llmClient = {
            chat: async () => JSON.stringify({
                steps: [
                    {
                        action: 'take',
                        item: 'dried meat',
                        target: null,
                        text: null,
                        note: null,
                        area: null,
                        until: null,
                        duration: null,
                    },
                    {
                        action: 'speak',
                        item: null,
                        target: null,
                        text: 'Hold on!',
                        note: null,
                        area: null,
                        until: null,
                        duration: null,
                    },
                ],
            }),
        };

        const steps = await PlanManager.generate('Rikka');
        assertEq(steps.length, 2, 'formats strict typed steps without grounding');
        assertEq(steps[0], 'take dried meat', 'formats take step');
        assertEq(steps[1], 'speak: "Hold on!"', 'formats speak step');
    });
});

test('PlanManager.generate injects goals, mosiac, relationships, and passes preview:true to buildMemoryContext', async () => {
    await withPlanManagerEnv(async () => {
        const realPB = globalThis.PromptBuilder;
        const origBuildMosiac = window.PromptBuilder ? window.PromptBuilder.buildMosiacContext : null;
        let capturedMemoryOpts = null;
        let capturedPrompt = '';

        worldState.data.players.Rikka.goals = [
            { id: 'find_shelter', what: 'Find shelter before nightfall', status: 'active', why: 'survive the storm', deadline: 42 },
            { id: 'old_goal', what: 'Already done goal', status: 'reached' },
        ];
        worldState.data.players.Rikka.mosiac = {
            M: 'Stay alive and protect companions',
            I: 'Find shelter before nightfall',
            O: [
                { id: 'ob_1', charge: 'Deliver medicine to Toma', status: 'accepted' },
                { id: 'ob_2', charge: 'Scout the ridge', from: 'Mira', status: 'offered', due: 50 },
            ],
            S: { day: 'morning patrol', step: { activity: 'guard gate', area: 'Camp' } },
        };
        worldState.data.players.Rikka.relationships = {
            Mira: { closeness: 60, label: 'ally' },
        };
        worldState.data.players_in_area = [{ name: 'Rikka' }, { name: 'Mira' }];

        // Provide real-style relationship & mosiac builders on the mocked PromptBuilder
        // (and verify PlanManager.generate calls buildMemoryContext with { preview: true }).
        globalThis.PromptBuilder = {
            buildRoomContext: () => 'Room: Camp',
            describeVitals: () => '',
            buildEmotionContext: () => '',
            buildRelationshipContext: () => '\nRikka considers Mira their ally (60/100)',
            buildMosiacContext: (p) => {
                const m = p.mosiac;
                return `\n=== YOUR MIND ===\nMotivation: ${m.M}\nIntention: ${m.I}\nPending Offers:\n  - "${m.O[1].charge}" from ${m.O[1].from}\nActive Obligations: ${m.O[0].charge}\nSchedule: ${m.S.day} (current: ${m.S.step.actionivity} at ${m.S.step.area})`;
            },
            buildMemoryContext: async (_charName, opts) => {
                capturedMemoryOpts = opts;
                return '=== I REMEMBER ===\nCampfire embers.';
            },
        };
        globalThis.llmClient = {
            chat: async (messages) => {
                capturedPrompt = messages[0].content;
                return JSON.stringify({
                    steps: [{ action: 'take', item: 'dried meat', target: null, text: null, note: null, area: null, until: null, duration: null }],
                });
            },
        };

        const steps = await PlanManager.generate('Rikka');
        assertEq(steps.length, 1, 'generates grounded plan');
        assertTrue(Boolean(capturedMemoryOpts && capturedMemoryOpts.preview === true), 'passes { preview: true } to buildMemoryContext');
        assertTrue(capturedPrompt.includes('=== YOUR GOALS ==='), 'includes goals header');
        assertTrue(capturedPrompt.includes('Find shelter before nightfall'), 'includes active goal');
        assertFalse(capturedPrompt.includes('Already done goal'), 'excludes reached goal');
        assertTrue(capturedPrompt.includes('Motivation: Stay alive and protect companions'), 'includes mosiac M');
        assertTrue(capturedPrompt.includes('Intention: Find shelter before nightfall'), 'includes mosiac I');
        assertTrue(capturedPrompt.includes('Active Obligations: Deliver medicine to Toma'), 'includes accepted obligation');
        assertTrue(capturedPrompt.includes('Scout the ridge'), 'includes pending offer');
        assertTrue(capturedPrompt.includes('Schedule: morning patrol'), 'includes schedule');
        assertTrue(capturedPrompt.includes('Rikka considers Mira their ally'), 'includes relationships');
        void realPB;
        void origBuildMosiac;
    });
});

test('PlanManager.hasPlan checks progress < plan.length', async () => {
    await withPlanManagerEnv(async () => {
        globalThis.PlanTracker = {
            getPlan: () => ['step 1', 'step 2'],
            getProgress: () => 1,
        };
        assertTrue(PlanManager.hasPlan('Rikka'), 'hasPlan true when progress < length');
        globalThis.PlanTracker.getProgress = () => 2;
        assertFalse(PlanManager.hasPlan('Rikka'), 'hasPlan false when progress >= length');
    });
});

test('PlanManager.generate delegates threat detection to ThreatDetector including turn_events and held weapons', async () => {
    await withPlanManagerEnv(async () => {
        let capturedPrompt = '';
        worldState.data.players.Raider = {
            name: 'Raider',
            current_area: 'Camp',
            state: 'idle',
            traits: {},
            relationships: {},
        };
        worldState.data.players_in_area = [
            { name: 'Rikka', holding: [] },
            { name: 'Raider', state: 'idle', holding: ['pistol'] },
        ];
        worldState.data.turn_events = [
            { actor: 'Raider', action: 'combat', target: 'Rikka', description: 'aims pistol at Rikka' },
        ];

        globalThis.llmClient = {
            chat: async (messages) => {
                capturedPrompt = messages[0].content;
                return JSON.stringify({
                    steps: [{ action: 'go', item: null, target: 'west passage', text: null, note: null, area: null, until: null, duration: null }],
                });
            },
        };

        await PlanManager.generate('Rikka');
        assertTrue(capturedPrompt.includes('IMMEDIATE DANGER'), 'PlanManager prompt includes ThreatDetector IMMEDIATE DANGER');
        assertTrue(capturedPrompt.includes('Raider'), 'PlanManager prompt names Raider');
        assertTrue(capturedPrompt.includes('pistol'), 'PlanManager prompt includes visible held weapon');

        // After Raider drops the pistol, PlanManager prompt no longer includes IMMEDIATE DANGER
        capturedPrompt = '';
        worldState.data.players_in_area = [
            { name: 'Rikka', holding: [] },
            { name: 'Raider', state: 'idle', holding: [] },
        ];
        worldState.data.turn_events = [
            { actor: 'Raider', action: 'drop', item: 'pistol', description: 'dropped the pistol' },
        ];

        await PlanManager.generate('Rikka');
        assertFalse(capturedPrompt.includes('IMMEDIATE DANGER'), 'PlanManager prompt clears danger after weapon drop');
    });
});

test('PlanManager.generate honors mental-verb intent parameter and Actions registers plan as free (task-984)', async () => {
    await withPlanManagerEnv(async () => {
        let capturedPrompt = '';
        globalThis.worldState = {
            data: {
                players: { Rikka: { name: 'Rikka', current_area: 'Camp', vitals: {} } },
                areas: { Camp: { name: 'Camp', exits: {} } },
            },
        };
        globalThis.PromptBuilder = {
            buildRoomContext: () => 'Room: Camp',
            describeVitals: () => '',
            buildEmotionContext: () => '',
            buildMemoryContext: async () => '',
        };
        globalThis.llmClient = {
            chat: async (messages) => {
                capturedPrompt = messages[0].content;
                return JSON.stringify({ steps: ['wait'] });
            },
        };

        const steps = await PlanManager.generate('Rikka', 'find the cellar key');
        assertEq(steps.length, 1, 'generates plan with intent');
        assertTrue(capturedPrompt.includes('Focus / intent for this plan: find the cellar key'), 'includes mental-verb intent in prompt');

        assertTrue(PlanGrounding.ACTIONS.has('plan'), 'PlanGrounding.ACTIONS includes plan');
    });
});
