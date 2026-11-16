/**
 * tools/unit/test_language_and_intermediator.js
 *
 * Targeted unit tests for:
 * - Phase 3: Intermediator (Reconsolidator) + Cue-Change Gate in PromptBuilder.buildMemoryContext
 * - Phase 4: Language & Lingo anti-omniscience gating in PromptBuilder.buildLanguageAndLingoContext
 */

test('PromptBuilder.buildLanguageAndLingoContext enforces anti-omniscience language and lingo limits', () => {
    var PB = window.PromptBuilder;
    assertTrue(typeof PB.buildLanguageAndLingoContext === 'function', 'buildLanguageAndLingoContext exists');

    const out = PB.buildLanguageAndLingoContext({
        name: 'Sammy',
        appearance: {
            capabilities: {
                languages: [
                    { language: 'English', fluency: 'native' },
                    { language: 'Spanish', fluency: 'basic', known_words: ['hola', 'gracias', 'abuela'] },
                ],
            },
            narrative: {
                lingo: ['skater lingo', 'kickflip', 'grind'],
            },
        },
    });

    assertTrue(out.includes('English (native)'), 'includes native English');
    assertTrue(out.includes('Spanish (basic) [only knows: hola, gracias, abuela]'), 'includes bounded Spanish vocabulary');
    assertTrue(out.includes('do NOT silently translate'), 'includes anti-omniscience directive');
    assertTrue(out.includes('skater lingo, kickflip, grind'), 'includes lingo');
});

test('PromptBuilder.buildMemoryContext runs Intermediator once per cue signature and caches unchanged cues', async () => {
    var PB = window.PromptBuilder;
    const prevPlayers = window.worldState.data?.players;
    const prevGetSpatial = window.ApiClient.getPlayerSpatialMemories;
    const prevRetrieve = window.ApiClient.retrievePlayerMemories;
    const prevReinforce = window.ApiClient.reinforcePlayerMemories;
    const prevGetMemClient = window.config.getMemoryLLMClient;
    const prevIntermediatorFlag = window.config.memoryIntermediator;
    const prevTickToRel = window.events?.tickToRelative;
    window.events = window.events || {};
    window.events.tickToRelative = (t) => `tick ${t ?? 0}`;

    let llmCalls = 0;
    window.worldState.data = window.worldState.data || {};
    window.worldState.data.players = {
        Sammy: {
            name: 'Sammy',
            current_area: 'Garage',
            emotion: { label: 'anxious' },
            memories: [
                { id: 'm1', text: 'Jake held the gun near Tyler.', category: 'episodic', tick: 10, importance: 8 },
            ],
        },
    };
    window.ApiClient.getPlayerSpatialMemories = async () => ({ spatial: '' });
    window.ApiClient.retrievePlayerMemories = async () => ({
        memories: [
            { id: 'm1', text: 'Jake held the gun near Tyler.', category: 'episodic', score: 3.5, source: 'associative' },
        ],
    });
    window.ApiClient.reinforcePlayerMemories = async () => ({});
    window.config.memoryIntermediator = true;
    window.config.getMemoryLLMClient = () => ({
        chat: async () => {
            llmCalls += 1;
            return `I remember Jake holding that gun near Tyler, and my stomach drops thinking about it (call ${llmCalls}).`;
        },
    });

    try {
        const first = await PB.buildMemoryContext('Sammy', { area: 'Garage' });
        assertTrue(first.includes('=== I REMEMBER (CONSCIOUS THOUGHT) ==='), `uses Intermediator conscious thought header (llmCalls=${llmCalls}, got=${first.slice(0, 200)})`);
        assertTrue(first.includes('(call 1)'), 'includes first LLM synthesis');
        assertTrue(llmCalls === 1, 'called Intermediator once');

        // Same cues -> Cue-Change Gate should reuse cached conscious thought without a 2nd LLM call
        const second = await PB.buildMemoryContext('Sammy', { area: 'Garage' });
        assertTrue(second.includes('(call 1)'), 'reuses cached conscious thought on unchanged cues');
        assertTrue(llmCalls === 1, 'did not re-call Intermediator when cues were unchanged');

        // Cue changes (new stimulus) -> Intermediator re-runs
        const third = await PB.buildMemoryContext('Sammy', { area: 'Garage', stimulus: 'Jake drops the gun' });
        assertTrue(third.includes('(call 2)'), 're-synthesizes when cues shift');
        assertTrue(llmCalls === 2, 'called Intermediator a second time after cue shift');
    } finally {
        if (prevPlayers !== undefined) window.worldState.data.players = prevPlayers;
        window.ApiClient.getPlayerSpatialMemories = prevGetSpatial;
        window.ApiClient.retrievePlayerMemories = prevRetrieve;
        window.ApiClient.reinforcePlayerMemories = prevReinforce;
        window.config.getMemoryLLMClient = prevGetMemClient;
        window.config.memoryIntermediator = prevIntermediatorFlag;
        if (prevTickToRel !== undefined) window.events.tickToRelative = prevTickToRel;
    }
});
