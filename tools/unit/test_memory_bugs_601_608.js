/**
 * test_memory_bugs_601_608.js
 *
 * Regression tests for bug-601, bug-602, and bug-604 on the JS side.
 */

if (typeof AgentMemory === 'undefined') {
    (0, eval)(__readFile('static/js/agent/memory-manager.js'));
}

test('bug-601: memory-view.js forwards entryId as memory_id in suppressMemory and unblockMemory', () => {
    const src = __readFile('static/js/inspector/memory-view.js');
    assertTrue(src.includes('memory_id: entryId'), 'suppressMemory/unblockMemory must forward memory_id: entryId');
    assertTrue(!src.includes('suppressPlayerMemory(charName, { tags: []'), 'Old empty-tags wildcard payload must be gone');
});

test('bug-602: buildMemoryContext populates semantic_scores under associative strategy and skips on preview', async () => {
    const origEmbed = window.EmbeddingClient;
    const origSearch = ApiClient.searchMemoryEmbeddings;
    const origRetrieve = ApiClient.retrievePlayerMemories;
    const origPlayers = worldState.data && worldState.data.players;
    const origTickToRelative = events.tickToRelative;
    const retrievedPayloads = [];
    let embedCalls = 0;

    try {
        worldState.data = worldState.data || {};
        worldState.data.players = {
            Lyrie: { current_area: 'Foyer', memories: [], vitals: {} }
        };
        events.tickToRelative = (t) => `tick ${t}`;
        window.EmbeddingClient = {
            configured: () => true,
            embed: async () => {
                embedCalls++;
                return [0.1, 0.2, 0.3];
            }
        };
        ApiClient.searchMemoryEmbeddings = async () => ({
            results: [{ memory_id: 'mem_sem_1', score: 0.88 }]
        });
        ApiClient.retrievePlayerMemories = async (_name, payload) => {
            retrievedPayloads.push(payload);
            return { memories: [] };
        };

        await PromptBuilder.buildMemoryContext('Lyrie', { area: 'Foyer', strategy: 'associative', preview: false, stimulus: 'missing key' });
        assertEq(embedCalls, 1, 'embed should be called once for non-preview associative');
        assertEq(retrievedPayloads.length, 1, 'retrievePlayerMemories should be called');
        assertEq(retrievedPayloads[0].cues.semantic_scores.mem_sem_1, 0.88, 'cues.semantic_scores should include hit');

        await PromptBuilder.buildMemoryContext('Lyrie', { area: 'Foyer', strategy: 'associative', preview: true, stimulus: 'missing key' });
        assertEq(embedCalls, 1, 'embed must NOT be called when preview=true');
    } finally {
        window.EmbeddingClient = origEmbed;
        ApiClient.searchMemoryEmbeddings = origSearch;
        ApiClient.retrievePlayerMemories = origRetrieve;
        events.tickToRelative = origTickToRelative;
        if (worldState.data) worldState.data.players = origPlayers;
    }
});

test('bug-604: AgentMemory.reflect skips already-reflected source_memory_ids and asks for closeness', async () => {
    const origGet = ApiClient.getPlayerMemories;
    const origReflect = ApiClient.reflectPlayerMemories;
    const origGetClient = config.getMemoryLLMClient;
    const origEmbed = window.EmbeddingClient;
    const origStoreEmbed = ApiClient.storeMemoryEmbeddings;
    const origTickToRelative = events.tickToRelative;
    let promptSeen = '';
    let sentSourceIds = [];
    const embeddedKeys = [];

    try {
        events.tickToRelative = (t) => `tick ${t}`;
        ApiClient.getPlayerMemories = async () => ({
            memories: [
                { id: 'm1', text: 'Old 1', tick: 1, importance: 8, reflection_depth: 0 },
                { id: 'm2', text: 'Old 2', tick: 2, importance: 8, reflection_depth: 0 },
                { id: 'm3', text: 'Old 3', tick: 3, importance: 8, reflection_depth: 0 },
                { id: 'r1', text: 'Existing reflection', tick: 4, importance: 8, reflection_depth: 1, source_memory_ids: ['m1', 'm2', 'm3'] },
                { id: 'm4', text: 'New 4', tick: 5, importance: 8, reflection_depth: 0 },
                { id: 'm5', text: 'New 5', tick: 6, importance: 8, reflection_depth: 0 },
                { id: 'm6', text: 'New 6', tick: 7, importance: 8, reflection_depth: 0 },
            ]
        });
        config.getMemoryLLMClient = () => ({
            chat: async (msgs) => {
                promptSeen = msgs[0].content;
                return JSON.stringify({
                    insights: [{
                        belief: 'New events show a clear shift in trust.',
                        about: ['Anna'],
                        confidence: 0.8,
                        emotional: null,
                        behavior: null,
                        relationship: null
                    }]
                });
            }
        });
        ApiClient.reflectPlayerMemories = async (_name, payload) => {
            sentSourceIds = payload.source_memory_ids;
            return { status: 'success', stored: 1, entries: [{ id: 'refl_new_1', text: 'New events show a clear shift in trust.' }] };
        };
        window.EmbeddingClient = {
            configured: () => true,
            embed: async () => [0.5, 0.5]
        };
        ApiClient.storeMemoryEmbeddings = async (payload) => {
            for (const item of payload.items || []) embeddedKeys.push(item.key);
            return { status: 'success' };
        };

        await AgentMemory.reflect('Lyrie');
        assertTrue(promptSeen.includes('closeness'), 'Reflection prompt should include closeness');
        assertEq(sentSourceIds.join(','), 'm4,m5,m6', 'Should skip already-reflected m1..m3');
        assertTrue(embeddedKeys.includes('Lyrie::refl_new_1'), 'Reflection entry should be embedded');
    } finally {
        ApiClient.getPlayerMemories = origGet;
        ApiClient.reflectPlayerMemories = origReflect;
        config.getMemoryLLMClient = origGetClient;
        window.EmbeddingClient = origEmbed;
        ApiClient.storeMemoryEmbeddings = origStoreEmbed;
        events.tickToRelative = origTickToRelative;
    }
});
