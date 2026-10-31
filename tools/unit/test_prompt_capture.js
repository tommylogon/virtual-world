/**
 * prompt-builder/capture.js - the shared "what would this character's turn
 * prompt be?" capture.
 *
 * The Benchmark Lab (/bench) sends the captured prompt to every model, so a
 * capture that quietly drops a section, follows the wrong room, or asks for a
 * different JSON shape than the live turn measures the wrong thing. These
 * tests drive the real prompt builder, not a stub of it.
 */

(() => {
    async function withFakeWorld(fn) {
        const previousData = window.worldState.data;
        const previousItems = window.worldState.getItemsInArea;
        const previousGetNode = window.worldState.getNode;
        const previousGetById = window.worldState.getNodeByIdentifier;
        const previousGraph = window.worldState.graph;
        const state = {
            current_area: 'library',
            time_ticks: 3,
            areas: {
                foyer: { name: 'foyer', description: 'A dusty entrance hall.', ambient_light: 40 },
                library: { name: 'library', description: 'Shelves of unread books.' },
            },
            players: {
                'sammy lopez': {
                    name: 'sammy lopez',
                    current_area: 'foyer',
                    personality: 'a nervous teenager who notices too much',
                    memories: [],
                    inventory: [],
                    traits: {},
                },
            },
        };
        window.worldState.data = state;
        window.worldState.graph = { nodes: {}, edges: [] };
        window.worldState.getItemsInArea = () => [];
        window.worldState.getNode = () => null;
        window.worldState.getNodeByIdentifier = () => null;
        try {
            return await fn(state);
        } finally {
            window.worldState.data = previousData;
            window.worldState.graph = previousGraph;
            window.worldState.getItemsInArea = previousItems;
            window.worldState.getNode = previousGetNode;
            window.worldState.getNodeByIdentifier = previousGetById;
        }
    }

    test('capture: the character own area wins over state.current_area', async () => {
        const captured = await withFakeWorld(() =>
            window.PromptBuilder.captureTurnPrompt('sammy lopez'));
        assertEq(captured.currentArea.name, 'foyer', 'capture follows the character, not the active player');
    });

    test('capture: the user prompt carries the live turn sections', async () => {
        const captured = await withFakeWorld(() =>
            window.PromptBuilder.captureTurnPrompt('sammy lopez'));
        assertTrue(captured.systemPrompt.includes('=== ACTIONS ==='), 'system prompt carries the action law');
        assertTrue(captured.userPrompt.includes('=== YOUR STATE ==='), 'user prompt carries the state block');
        assertTrue(captured.userPrompt.includes('You are sammy lopez. Personality:'), 'the persona is in the prompt');
        assertTrue(captured.userPrompt.includes('You are currently in the foyer'), 'the prompt describes the character own room');
    });

    test('capture: the JSON example matches the live think-decide shape', async () => {
        const captured = await withFakeWorld(() =>
            window.PromptBuilder.captureTurnPrompt('sammy lopez'));
        assertTrue(captured.userPrompt.includes('"learned_names"'), 'the example asks for learned_names');
        assertTrue(captured.userPrompt.includes('"emotion":{"label":"unsettled"'), 'the example asks for the emotion object');
    });

    test('capture: an unknown character is an error, not an empty prompt', async () => {
        let message = '';
        try {
            await window.PromptBuilder.captureTurnPrompt('nobody at all');
        } catch (err) {
            message = String(err && err.message || err);
        }
        assertTrue(message.includes('nobody at all'), 'the error names the character');
    });
})();
