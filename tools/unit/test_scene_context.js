/**
 * test_scene_context.js - Verify dynamic scene context (Current Situation) is injected into prompt context.
 */

(() => {
    function withFakeWorld(fn) {
        const previousData = window.worldState.data;
        const previousItems = window.worldState.getItemsInArea;
        const previousGetNode = window.worldState.getNode;
        const previousGetById = window.worldState.getNodeByIdentifier;
        const previousGraph = window.worldState.graph;
        const state = {
            current_area: 'area_cafeteria',
            time_ticks: 0,
            areas: {
                area_cafeteria: {
                    id: 'area_cafeteria',
                    name: 'Millwood High Cafeteria',
                    description: 'A crowded lunchroom.'
                }
            },
            players: {
                'kayla jenkins': {
                    name: 'kayla jenkins',
                    current_area: 'area_cafeteria',
                    personality: 'sharp-tongued',
                    memories: [],
                    inventory: [],
                    traits: {},
                }
            }
        };
        window.worldState.data = state;
        window.worldState.graph = { nodes: {}, edges: [] };
        window.worldState.getItemsInArea = () => [];
        window.worldState.getNode = () => null;
        window.worldState.getNodeByIdentifier = () => null;
        try {
            return fn(state);
        } finally {
            window.worldState.data = previousData;
            window.worldState.graph = previousGraph;
            window.worldState.getItemsInArea = previousItems;
            window.worldState.getNode = previousGetNode;
            window.worldState.getNodeByIdentifier = previousGetById;
        }
    }

    test('scene_context injects Current Situation block into room context parts', () => {
        withFakeWorld((state) => {
            state.scene_context = {
                title: 'The Crimson Gel Pen Note',
                premise: 'Jake just revealed a mysterious note written in crimson gel pen.',
                tick_started: 0
            };
            const player = state.players['kayla jenkins'];
            const parts = window.PromptBuilder.buildRoomContextParts(state, 'kayla jenkins', player, state.areas.area_cafeteria);

            assertTrue(Boolean(parts.extraNote), 'extraNote must be populated when scene_context exists');
            assertTrue(parts.extraNote.includes('=== CURRENT SITUATION (The Crimson Gel Pen Note) ==='), 'header must format title');
            assertTrue(parts.extraNote.includes('Jake just revealed a mysterious note written in crimson gel pen.'), 'premise must be present');
        });
    });

    test('scene_context is omitted when premise is missing', () => {
        withFakeWorld((state) => {
            delete state.scene_context;
            const player = state.players['kayla jenkins'];
            const parts = window.PromptBuilder.buildRoomContextParts(state, 'kayla jenkins', player, state.areas.area_cafeteria);

            assertEq(parts.extraNote, '', 'extraNote must be empty when no scene_context is set');
        });
    });
})();
