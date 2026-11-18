/**
 * tools/unit/test_memory_weaver.js
 *
 * Unit tests for the Memory Weaver & Unified Editor (task-730, task-785, bug-519):
 * - relative time parser (`InspectorMemory.parseRelativeTime`)
 * - Weaver response parser & editorial-leakage guard (`parseWeaverResponse`, `stripEditorialLeakage`)
 * - grounded identity & multi-turn message builder (`_identityBlock`, `buildWeaverMessages`)
 * - Mind panel underlying record & lived_log evidence inspector (`InspectorMindView._recordAndEvidenceHtml`)
 */

test('InspectorMemory.parseRelativeTime resolves natural-language relative time expressions (task-730)', () => {
    const IM = window.InspectorMemory;
    assertTrue(typeof IM.parseRelativeTime === 'function', 'parseRelativeTime exists');

    assertEq(IM.parseRelativeTime('now', 500, 1).tick, 500, 'now -> currentTick');
    assertEq(IM.parseRelativeTime('30 minutes ago', 500, 1).tick, 470, '30m ago at 1m/tick');
    assertEq(IM.parseRelativeTime('2 hours ago', 500, 2).tick, 440, '2h ago at 2m/tick -> -60 ticks');
    assertEq(IM.parseRelativeTime('yesterday', 2000, 1).tick, 560, 'yesterday at 1m/tick -> -1440 ticks');
    assertEq(IM.parseRelativeTime('3 days ago', 5000, 1).tick, 680, '3d ago at 1m/tick -> -4320 ticks');
    assertEq(IM.parseRelativeTime('100 turns before start', 500, 1).tick, -100, 'turns before start -> negative tick');
    assertEq(IM.parseRelativeTime('tick -250', 500, 1).tick, -250, 'explicit negative tick');
    assertEq(IM.parseRelativeTime('', 500, 1), null, 'empty string returns null');

    const clamped = IM.parseRelativeTime('10 years ago', 100, 5, -50000);
    assertTrue(clamped.beforeBirth === true, 'flags beforeBirth when earlier than birthTick');
    assertEq(clamped.tick, -50000, 'clamps tick to birthTick floor');
    assertTrue(clamped.unclampedTick < -50000, 'preserves unclampedTick for diagnostics');
});

test('InspectorMemory.parseWeaverResponse separates character_reply from memory.text and strips editorial commentary (bug-519)', () => {
    const IM = window.InspectorMemory;
    const raw = '```json\n' + JSON.stringify({
        character_reply: 'That horror film gave me chills for a week, especially the attic scene.',
        memory: {
            text: 'I watched The Attic Lantern with Miki last night; the creaking floorboards in the third act left me checking the hall lock twice.\n\nNote: This memory captures Vera\'s cautious nature and her bond with Miki.',
            type: 'reflection',
            category: 'belief',
            importance: 7,
            confidence: 0.9,
            tick_offset_minutes: -1440,
            location: 'Living Room',
            entities: ['Miki', 'Living Room'],
            tags: ['cinema', 'suspense'],
            memory_emotions: [{ label: 'spooked', intensity: 7 }, { label: 'amused', intensity: 4 }],
            relationship_deltas: [
                { who: 'Miki', why: 'Shared a movie night together', data: { familiarity: 2, trust: 1.5, attraction: 99 } }
            ],
            derived_expectation: 'When I come home late, I double-check the hall lock before going to bed.'
        },
        counterpart_memory: {
            who: 'Miki',
            text: 'Vera jumped at every creak during The Attic Lantern, though she pretended she was only checking the draft.',
            importance: 6,
            memory_emotions: [{ label: 'amused', intensity: 7 }],
            relationship_deltas: [{ who: 'Vera', why: 'Watched a movie together', data: { familiarity: 2 } }]
        }
    }) + '\n```';

    const parsed = IM.parseWeaverResponse(raw);
    assertTrue(parsed !== null, 'parsed weaver response is non-null');
    assertEq(
        parsed.character_reply,
        'That horror film gave me chills for a week, especially the attic scene.',
        'character_reply extracted separately'
    );
    assertEq(
        parsed.text,
        'I watched The Attic Lantern with Miki last night; the creaking floorboards in the third act left me checking the hall lock twice.',
        'editorial second paragraph stripped from memory.text'
    );
    assertFalse(parsed.text.includes('That horror film gave me chills'), 'character_reply never concatenated into memory.text');
    assertEq(parsed.category, 'belief', 'category preserved');
    assertEq(parsed.importance, 7, 'importance preserved');
    assertEq(parsed.tick_offset_minutes, -1440, 'tick_offset_minutes preserved');
    assertEq(parsed.relationship_deltas.length, 1, 'relationship_deltas parsed');
    assertEq(parsed.relationship_deltas[0].who, 'Miki', 'relationship delta target');
    assertEq(parsed.relationship_deltas[0].data.attraction, 5, 'delta clamped to +5 max');
    assertTrue(parsed.counterpart_memory !== null, 'counterpart_memory parsed');
    assertEq(parsed.counterpart_memory.who, 'Miki', 'counterpart target');
});

test('InspectorMemory._identityBlock grounds voice in persona summary, recalled memories, and people profiles (task-730)', () => {
    const IM = window.InspectorMemory;
    const bundle = {
        persona_summary: {
            personality: 'Sharp-witted and skeptical.',
            base_description: 'Awatchmaker with brass spectacles.',
            values: ['precision', 'honesty'],
            fears: ['deep water'],
            likes: ['clockwork']
        },
        current_emotion: { current: 'curious', intensity: 0.7 },
        recalled_memories: [
            { tick: 42, text: 'I repaired the mainspring on Rex\'s pocket watch.' }
        ],
        people_profiles: [
            { name: 'Rex', profile: { role: 'friend', trust: 35, fear: 0, attraction: 5, respect: 25 } }
        ]
    };
    const block = IM._identityBlock('Vera', bundle);
    assertTrue(block.includes('Sharp-witted and skeptical.'), 'includes personality');
    assertTrue(block.includes('precision, honesty'), 'includes values');
    assertTrue(block.includes('deep water'), 'includes fears');
    assertTrue(block.includes('mainspring on Rex\'s pocket watch'), 'includes recalled memories');
    assertTrue(block.includes('Rex (friend): trust 35'), 'includes derived person profile');
});

test('InspectorMindView._recordAndEvidenceHtml renders underlying record fields and matching lived_log rows (task-785)', () => {
    const MV = window.InspectorMindView;
    assertTrue(typeof MV._recordAndEvidenceHtml === 'function', '_recordAndEvidenceHtml exists');

    const prevPlayers = window.worldState.players;
    window.worldState.players = {
        Vera: {
            lived_log: [
                {
                    tick: 120,
                    kind: 'relationship',
                    what: 'closeness toward Rex +5',
                    why: 'social:gift',
                    area: 'Kitchen',
                    tags: ['rel:Rex', 'gift']
                }
            ]
        }
    };
    try {
        const mem = {
            id: 'mem_120_abc',
            text: 'Rex handed me a warm loaf of bread in the Kitchen.',
            tick: 120,
            source: 'manual',
            type: 'event',
            category: 'social',
            location: 'Kitchen',
            entity_ids: ['player_rex', 'area_kitchen'],
            tags: ['rel:Rex', 'food']
        };
        const html = MV._recordAndEvidenceHtml(mem, 'Vera');
        assertTrue(html.includes('mem_120_abc'), 'renders memory id');
        assertTrue(html.includes('Kitchen'), 'renders location');
        assertTrue(html.includes('player_rex, area_kitchen'), 'renders entity_ids');
        assertTrue(html.includes('closeness toward Rex +5'), 'renders matching lived_log evidence');
        assertTrue(html.includes('social:gift'), 'renders lived_log why');

        const unlinkedMem = {
            id: 'mem_999_none',
            text: 'A distant childhood memory.',
            tick: -500,
            source: 'manual',
            type: 'memory'
        };
        const emptyHtml = MV._recordAndEvidenceHtml(unlinkedMem, 'Vera');
        assertTrue(emptyHtml.includes('No lived-log entries linked to this memory.'), 'explicit empty state when no lived_log matches');
    } finally {
        window.worldState.players = prevPlayers;
    }
});

test('InspectorMemory.extractInlineTimeExpr and parseWeaverResponse bundle parsing (task-986)', () => {
    const MV = window.InspectorMemory;
    assertEq(
        MV.extractInlineTimeExpr('remember that time you almost skated right into traffic when you were 12 and Kyrie tackled you'),
        'age 12',
        'extracts inline "when you were 12" phrase'
    );
    assertEq(
        MV.extractInlineTimeExpr('At age 16 she broke her wrist on the rail'),
        'age 16',
        'extracts inline "at age 16" phrase'
    );
    assertEq(
        MV.extractInlineTimeExpr('3 days ago we argued in the diner'),
        '3 days ago',
        'extracts inline relative days phrase'
    );

    const parsedAge12 = MV.parseRelativeTime('age 12', 100, 5, -2000000, 17);
    assertTrue(Boolean(parsedAge12 && parsedAge12.tick < 0), 'age 12 resolves to pre-scenario negative tick');

    const parsed = MV.parseWeaverResponse(JSON.stringify({
        character_reply: 'Ugh, don\'t remind me of that deck.',
        memory: {
            text: 'I nearly skated into traffic at 12 and Kyrie tackled me off the board.',
            type: 'event',
            category: 'episodic',
            importance: 7,
            confidence: 0.9,
        },
        bundle: [
            {
                type: 'observation',
                category: 'episodic',
                text: 'My skateboard snapped cleanly under us on the curb.',
                importance: 6,
                confidence: 0.9,
            },
            {
                type: 'thought',
                category: 'belief',
                text: 'Kyrie ruined my board on purpose and owes me a new one.',
                importance: 7,
                confidence: 0.8,
            },
            {
                type: 'event',
                category: 'episodic',
                text: 'I nearly skated into traffic at 12 and Kyrie tackled me off the board.',
            }
        ],
        counterpart_memory: {
            who: 'Kyrie',
            text: 'I tackled them out of oncoming traffic at 12 and their board broke.',
            importance: 7,
        }
    }));

    assertEq(parsed.type, 'event', 'primary record is event');
    assertEq(parsed.bundle.length, 2, 'parses 2 distinct companion bundle records (deduping identical text)');
    assertEq(parsed.bundle[0].type, 'observation', 'first bundle item is observation');
    assertEq(parsed.bundle[1].type, 'thought', 'second bundle item is thought');
    assertEq(parsed.bundle[1].category, 'belief', 'second bundle item has belief category');
    assertEq(parsed.counterpart_memory.who, 'Kyrie', 'preserves counterpart memory');
});

test('InspectorMemory.runIntrusiveThoughtPipeline and commitIntrusiveThought run time-locked Recall -> Intermediator -> Thought (task-987)', async () => {
    const MV = window.InspectorMemory;
    const prevApi = window.ApiClient;
    const prevPB = window.PromptBuilder;
    const prevLLM = window.VW.llm;
    const prevFetch = window.worldState.fetch;
    try {
        let synthOpts = null;
        let savedPayload = null;
        window.ApiClient = {
            ...prevApi,
            getPlayerMemoriesContext: async (_charName, body) => {
                if (body && body.candidate) {
                    return {
                        current_tick: 120,
                        current_world_datetime: '2016-05-14T18:00:00',
                        contradictions_preview: [{ id: 'mem_age12_belief' }],
                    };
                }
                return {
                    current_tick: 120,
                    current_world_datetime: '2016-05-14T18:00:00',
                    time_per_tick_minutes: 5,
                    current_emotion: { current: 'reflective', intensity: 4 },
                    recalled_memories: [
                        { id: 'mem_age12_evt', text: 'Kyrie tackled me out of traffic at 12 and my board snapped.', tick: -525600, world_datetime: '2011-05-14T15:00:00', type: 'event', category: 'episodic' },
                        { id: 'mem_age12_belief', text: 'Kyrie ruined my skateboard on purpose.', tick: -525600, world_datetime: '2011-05-14T15:00:00', type: 'thought', category: 'belief' },
                        { id: 'mem_future_leak', text: 'Future 2024 memory that must be locked out.', tick: 999, world_datetime: '2024-01-01T00:00:00', type: 'event', category: 'episodic' },
                    ],
                };
            },
            addPlayerMemory: async (_charName, payload) => {
                savedPayload = payload;
                return { entry: { id: 'mem_now_thought' } };
            },
        };
        window.PromptBuilder = {
            ...(prevPB || {}),
            synthesizeConsciousThought: async (_charName, _area, _actors, _dialogue, _emo, topMems, _sig, _rep, opts) => {
                synthOpts = { count: topMems.length, skipPersist: opts?.skipPersist };
                return 'Kyrie knocked me onto the pavement when I was 12; the deck broke, even though a truck was right there.';
            },
        };
        window.VW.llm = {
            chat: async () => JSON.stringify({
                thought: 'She did not ruin my board out of spite - she saved me from oncoming traffic and I was too stubborn at 12 to admit it.',
                importance: 8,
            }),
        };
        window.worldState.fetch = async () => {};

        const res = await MV.runIntrusiveThoughtPipeline('Vera', 'Why did I blame Kyrie for my broken skateboard?', ['mem_age12_evt', 'mem_age12_belief']);
        assertEq(res.currentTick, 120, 'pipeline resolves currentTick');
        assertEq(res.recalledMemories.length, 2, 'time-locks out future memories (tick 999 / 2024)');
        assertEq(synthOpts.count, 2, 'Intermediator receives only time-locked memories');
        assertEq(synthOpts.skipPersist, true, 'Intermediator runs with skipPersist:true during staging');
        assertTrue(res.presentThought.includes('saved me from oncoming traffic'), 'captures present-day Character Thought');
        assertEq(res.sourceMemoryIds.join(','), 'mem_age12_evt,mem_age12_belief', 'links recalled source memory IDs');
        assertEq(res.contradicts.join(','), 'mem_age12_belief', 'detects contradiction against age-12 blame belief');

        await MV.commitIntrusiveThought('Vera');
        assertTrue(Boolean(savedPayload), 'commits present-day thought');
        assertEq(savedPayload.type, 'thought', 'committed record is type thought');
        assertEq(savedPayload.category, 'belief', 'committed record is category belief');
        assertEq(savedPayload.tick, 120, 'committed record is stamped at current_tick (120), not age 12');
        assertEq(savedPayload.source_memory_ids.join(','), 'mem_age12_evt,mem_age12_belief', 'preserves source_memory_ids lineage');
        assertEq(savedPayload.contradicts.join(','), 'mem_age12_belief', 'preserves contradicts lineage');
    } finally {
        window.ApiClient = prevApi;
        window.PromptBuilder = prevPB;
        window.VW.llm = prevLLM;
        window.worldState.fetch = prevFetch;
    }
});
