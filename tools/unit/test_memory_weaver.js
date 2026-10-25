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
