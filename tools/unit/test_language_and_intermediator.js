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

test('Strict Actor Isolation (task-949): buildMemoryContext never emits raw stored memory rows or investigation notes', async () => {
    var PB = window.PromptBuilder;
    const prevPlayers = window.worldState.data?.players;
    const prevGetSpatial = window.ApiClient.getPlayerSpatialMemories;
    const prevRetrieve = window.ApiClient.retrievePlayerMemories;
    const prevReinforce = window.ApiClient.reinforcePlayerMemories;
    const prevGetMemClient = window.config.getMemoryLLMClient;
    const prevIntermediatorFlag = window.config.memoryIntermediator;
    const prevTickToRel = window.events?.tickToRelative;
    const prevFetch = globalThis.fetch;
    window.events = window.events || {};
    window.events.tickToRelative = (t) => `tick ${t ?? 0}`;

    const fetchUrls = [];
    globalThis.fetch = async (url) => {
        fetchUrls.push(String(url));
        return { ok: true, json: async () => ({}) };
    };

    window.worldState.data = window.worldState.data || {};
    window.worldState.data.players = {
        Sammy: {
            name: 'Sammy',
            current_area: 'Garage',
            emotion: { label: 'anxious' },
            memories: [
                { id: 'm1', text: 'RAW_SECRET_MARKER_123', category: 'episodic', tick: 10, importance: 8 },
                { id: 'm2', text: 'examine locker: RAW_INVESTIGATION_MARKER_456.', category: 'episodic', tick: 11, importance: 5 },
            ],
        },
    };
    window.ApiClient.getPlayerSpatialMemories = async () => ({ spatial: '' });
    window.ApiClient.retrievePlayerMemories = async () => ({
        memories: [
            { id: 'm1', text: 'RAW_SECRET_MARKER_123', category: 'episodic', score: 3.5, source: 'associative' },
            { id: 'm2', text: 'examine locker: RAW_INVESTIGATION_MARKER_456.', category: 'episodic', score: 2.0, source: 'keyword' },
        ],
    });
    window.ApiClient.reinforcePlayerMemories = async () => ({});
    window.config.memoryIntermediator = true;

    try {
        // 1. Preview mode (planning) runs Intermediator without persisting and emits zero raw memory rows
        window.config.getMemoryLLMClient = () => ({
            chat: async () => 'I keep thinking about the garage and what I saw near the locker.',
        });
        const previewCtx = await PB.buildMemoryContext('Sammy', { area: 'Garage', preview: true, stimulus: 'locker' });
        assertTrue(previewCtx.includes('=== I REMEMBER (CONSCIOUS THOUGHT) ==='), 'preview includes conscious thought header');
        assertTrue(previewCtx.includes('what I saw near the locker'), 'preview includes synthesized conscious thought');
        assertTrue(!previewCtx.includes('RAW_SECRET_MARKER_123'), 'preview must not leak raw memory text');
        assertTrue(!previewCtx.includes('RAW_INVESTIGATION_MARKER_456'), 'preview must not leak raw investigation notes');
        assertTrue(!previewCtx.includes('=== MY INVESTIGATION NOTES ==='), 'investigation notes block is removed');
        assertTrue(!fetchUrls.some((u) => u.includes('/memories/entry')), 'preview must not persist reflection memory');

        // 2. Fallback when Intermediator LLM is unavailable still emits zero raw memory rows
        window.config.getMemoryLLMClient = () => null;
        const fallbackCtx = await PB.buildMemoryContext('Sammy', { area: 'Garage', stimulus: 'new cue' });
        assertTrue(!fallbackCtx.includes('RAW_SECRET_MARKER_123'), 'fallback must not leak raw memory text');
        assertTrue(!fallbackCtx.includes('EVENTS - what happened'), 'fallback must not emit raw category lists');
        assertTrue(fallbackCtx.includes("You don't remember anything relevant right now."), 'fallback emits neutral empty state');
    } finally {
        globalThis.fetch = prevFetch;
        if (prevPlayers !== undefined) window.worldState.data.players = prevPlayers;
        window.ApiClient.getPlayerSpatialMemories = prevGetSpatial;
        window.ApiClient.retrievePlayerMemories = prevRetrieve;
        window.ApiClient.reinforcePlayerMemories = prevReinforce;
        window.config.getMemoryLLMClient = prevGetMemClient;
        window.config.memoryIntermediator = prevIntermediatorFlag;
        if (prevTickToRel !== undefined) window.events.tickToRelative = prevTickToRel;
    }
});

test('Strict Actor Isolation (task-949): turn-prompts retire endOfTurnMemory and Reactor memory-creation schema', () => {
    var PB = window.PromptBuilder;
    const player = { name: 'Sammy', state: 'idle', personality: 'Observant' };
    const parts = { tickHead: 'Tick 1', roomBody: 'You are in the Garage.' };

    const reactionPrompt = PB.buildReactionPrompt(player, parts, 'Healthy', 'Neutral', '', '=== I REMEMBER (CONSCIOUS THOUGHT) ===\nStay sharp.', '', true, false);
    assertTrue(!reactionPrompt.includes('"memory"'), 'buildReactionPrompt must not request memory field even when includeMemory=true');
    assertTrue(!reactionPrompt.includes('Write a first-person'), 'buildReactionPrompt must not include MEMORY_INSTRUCTION_REACT');

    const reactPrompt = PB.buildResultReactionPrompt('Sammy', player, 'Garage', 'Healthy', 'Neutral', '', 'Check it.', 'examine bench', 'Dusty bench.', '=== I REMEMBER (CONSCIOUS THOUGHT) ===\nStay sharp.', '');
    assertTrue(!reactPrompt.includes('"memory"'), 'buildResultReactionPrompt must not request memory field');
    assertTrue(!reactPrompt.includes('Write a first-person'), 'buildResultReactionPrompt must not include MEMORY_INSTRUCTION_REACT');
    assertTrue(!('endOfTurnMemory' in (window.CONFIG_SCHEMA || {})), 'endOfTurnMemory is retired from CONFIG_SCHEMA');
});
