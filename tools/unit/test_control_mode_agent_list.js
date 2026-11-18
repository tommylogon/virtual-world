'use strict';

const StreamControlMode = new Function(
    window.__readFile('static/js/stream/stream-control-mode.js') + '; return StreamControlMode;'
)();

test('worldState.fetch() with active _runtimeFocus returns worldState.data preserving all characters', async () => {
    const state = new WorldState();
    state.data = {
        players: {
            Alice: { id: 'character/alice', name: 'Alice', controller: 'agent', autonomy: true, simple_npc: false, current_area: 'Hall' },
            Bob: { id: 'character/bob', name: 'Bob', controller: 'agent', autonomy: true, simple_npc: false, current_area: 'Kitchen' },
            Clara: { id: 'character/clara', name: 'Clara', controller: 'simple', autonomy: true, simple_npc: true, current_area: 'Garden' }
        },
        areas: {
            Hall: { id: 'area/hall', name: 'Hall' },
            Kitchen: { id: 'area/kitchen', name: 'Kitchen' },
            Garden: { id: 'area/garden', name: 'Garden' }
        },
        areas_by_id: {
            'area/hall': { id: 'area/hall', name: 'Hall' }
        },
        graph: {
            nodes: {
                'character/alice': { id: 'character/alice', type: 'character', name: 'Alice' },
                'character/bob': { id: 'character/bob', type: 'character', name: 'Bob' },
                'character/clara': { id: 'character/clara', type: 'character', name: 'Clara' },
                'area/hall': { id: 'area/hall', type: 'area', name: 'Hall' }
            },
            edges: []
        }
    };
    state.setRuntimeFocusForCharacter('Alice');
    assertEq(state._runtimeFocus, ['character/alice'], 'runtime focus is set to Alice');

    const originalFetch = window.fetch;
    window.fetch = (url) => {
        assertTrue(String(url).includes('/api/runtime/state?character_id=character%2Falice'),
            'fetches scoped runtime state for focused character');
        return Promise.resolve({
            ok: true,
            json: async () => ({
                snapshot_type: 'character_runtime',
                character_ids: ['character/alice'],
                players: {
                    Alice: {
                        id: 'character/alice',
                        name: 'Alice',
                        controller: 'human',
                        autonomy: false,
                        simple_npc: false,
                        current_area: 'Hall',
                        turn_slots: { major: 1, minor: 1, free: 3 }
                    }
                },
                player_node_ids: { Alice: 'character/alice' },
                areas_by_id: { 'area/hall': { id: 'area/hall', name: 'Hall' } },
                graph: {
                    nodes: {
                        'character/alice': { id: 'character/alice', type: 'character', name: 'Alice', properties: {} },
                        'area/hall': { id: 'area/hall', type: 'area', name: 'Hall', properties: {} }
                    },
                    edges: []
                },
                turn_events: [],
                time_ticks: 5
            })
        });
    };

    try {
        const result = await state.fetch();
        assertEq(result, state.data, 'fetch() returns worldState.data rather than character_runtime snapshot');
        assertEq(Object.keys(result.players).sort(), ['Alice', 'Bob', 'Clara'],
            'all scenario characters remain present in returned state');
        assertEq(result.players.Alice.controller, 'human', 'focused character updates are merged into worldState.data');
        assertEq(result.players.Bob.current_area, 'Kitchen', 'other characters are preserved intact');
    } finally {
        if (originalFetch === undefined) delete window.fetch;
        else window.fetch = originalFetch;
    }
});

test('toggling control mode to human does not collapse #agent-list to a single character', async () => {
    const prevWorldState = window.worldState;
    const prevApiClient = window.ApiClient;
    const prevConfig = window.config;
    const prevVW = window.VW;
    const prevTurnQueue = window.TurnQueue;
    const prevFetch = window.fetch;

    const state = new WorldState();
    state.data = {
        active_player: 'Alice',
        players: {
            Alice: { id: 'character/alice', name: 'Alice', controller: 'agent', autonomy: true, simple_npc: false, current_area: 'Hall' },
            Bob: { id: 'character/bob', name: 'Bob', controller: 'agent', autonomy: true, simple_npc: false, current_area: 'Kitchen' },
            Clara: { id: 'character/clara', name: 'Clara', controller: 'simple', autonomy: true, simple_npc: true, current_area: 'Garden' }
        },
        areas: {},
        areas_by_id: {},
        graph: { nodes: {}, edges: [] }
    };

    const renderedAgentLists = [];
    window.worldState = state;
    window.config = { controllingPlayer: null };
    window.TurnQueue = { reconcile: () => {} };
    window.ApiClient = {
        updateCharacter: async (charName, payload) => ({ ok: true, charName, payload })
    };
    window.VW = {
        ui: {
            renderAll: (renderedState) => {
                renderedAgentLists.push(Object.keys(renderedState.players || {}).sort());
            }
        }
    };
    window.fetch = () => Promise.resolve({
        ok: true,
        json: async () => ({
            snapshot_type: 'character_runtime',
            character_ids: ['character/alice'],
            players: {
                Alice: {
                    id: 'character/alice',
                    name: 'Alice',
                    controller: 'human',
                    autonomy: false,
                    simple_npc: false,
                    current_area: 'Hall'
                }
            },
            player_node_ids: { Alice: 'character/alice' },
            areas_by_id: {},
            graph: { nodes: {}, edges: [] },
            turn_events: [],
            time_ticks: 2
        })
    });

    try {
        const scm = new StreamControlMode({});
        await scm.setControlMode('Alice', 'human');

        assertEq(window.config.controllingPlayer, 'Alice', 'controllingPlayer updated to Alice');
        assertEq(state._runtimeFocus, ['character/alice'], 'runtime focus set to Alice');
        assertEq(renderedAgentLists.length, 1, 'renderAll called once after control mode toggle');
        assertEq(renderedAgentLists[0], ['Alice', 'Bob', 'Clara'],
            '#agent-list receives all scenario characters instead of collapsing to single active character');
    } finally {
        window.worldState = prevWorldState;
        if (prevApiClient === undefined) delete window.ApiClient;
        else window.ApiClient = prevApiClient;
        window.config = prevConfig;
        window.VW = prevVW;
        if (prevTurnQueue === undefined) delete window.TurnQueue;
        else window.TurnQueue = prevTurnQueue;
        if (prevFetch === undefined) delete window.fetch;
        else window.fetch = prevFetch;
    }
});
