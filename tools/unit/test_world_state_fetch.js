'use strict';

test('a coalesced state fetch resolves after the trailing refresh', async () => {
    const state = new WorldState();
    const originalFetch = window.fetch;
    let requestCount = 0;
    let resolveFirst;
    window.fetch = () => {
        requestCount += 1;
        if (requestCount === 1) {
            return new Promise(resolve => { resolveFirst = resolve; });
        }
        return Promise.resolve({
            json: async () => ({
                players: {
                    Explorer: {
                        turn_slots: { major: 0, minor: 1, free: 3, activity: 1 }
                    }
                }
            })
        });
    };

    try {
        const initialFetch = state.fetch();
        await Promise.resolve();
        const afterActionFetch = state.fetch();
        resolveFirst({
            json: async () => ({
                players: {
                    Explorer: {
                        turn_slots: { major: 1, minor: 1, free: 3, activity: 1 }
                    }
                }
            })
        });

        const freshState = await afterActionFetch;
        await initialFetch;
        assertEq(requestCount, 2, 'one trailing state request ran');
        assertEq(freshState.players.Explorer.turn_slots,
            { major: 0, minor: 1, free: 3, activity: 1 },
            'callers receive the post-action slot budget');
    } finally {
        if (originalFetch === undefined) delete window.fetch;
        else window.fetch = originalFetch;
    }
});

test('a focused runtime snapshot never replaces the global world cache', async () => {
    const state = new WorldState();
    const globalState = { graph: { nodes: { whole_world: {} } } };
    state.data = globalState;
    const originalFetch = window.fetch;
    let requestedUrl = '';
    window.fetch = (url) => {
        requestedUrl = url;
        return Promise.resolve({
            ok: true,
            json: async () => ({
                snapshot_type: 'character_runtime',
                character_ids: ['character/alice'],
                players: { Alice: { turn_slots: { major: 0, minor: 1, free: 3 } } }
            })
        });
    };

    try {
        const runtime = await state.fetchRuntime(['character/alice']);
        assertTrue(requestedUrl.includes('character_id=character%2Falice'), 'requests the stable ID');
        assertEq(runtime.snapshot_type, 'character_runtime', 'returns the focused projection');
        assertEq(state.runtimeData, runtime, 'stores the focused projection separately');
        assertEq(state.data, globalState, 'leaves the global/editor snapshot untouched');
        assertEq(state.runtimePlayer('Alice').turn_slots,
            { major: 0, minor: 1, free: 3 }, 'focused player state is available to the composer');
    } finally {
        if (originalFetch === undefined) delete window.fetch;
        else window.fetch = originalFetch;
    }
});

test('focused snapshots patch only their working set into the global cache', () => {
    const state = new WorldState();
    const playerNodeId = 'character/alice';
    state.data = {
        graph: {
            nodes: {
                old_room: { id: 'old_room', type: 'area', name: 'Old Room' },
                new_room: { id: 'new_room', type: 'area', name: 'New Room' },
                [playerNodeId]: { id: playerNodeId, type: 'character', name: 'Alice' },
                distant: { id: 'distant', type: 'area', name: 'Distant' }
            },
            edges: [
                { source: playerNodeId, target: 'old_room', type: 'in', properties: {} },
                { source: 'distant', target: 'distant', type: 'loop', properties: {} }
            ]
        },
        players: { Alice: { current_area: 'Old Room' } },
        areas: { 'Old Room': { id: 'old_room', name: 'Old Room' } },
        areas_by_id: { old_room: { id: 'old_room', name: 'Old Room' } },
        time_ticks: 1
    };
    const snapshot = {
        snapshot_type: 'character_runtime',
        players: { Alice: { current_area: 'New Room', turn_slots: { major: 0, minor: 1, free: 3 } } },
        player_node_ids: { Alice: playerNodeId },
        areas_by_id: { new_room: { id: 'new_room', name: 'New Room' } },
        graph: {
            nodes: {
                new_room: { id: 'new_room', type: 'area', name: 'New Room', properties: {} },
                [playerNodeId]: { id: playerNodeId, type: 'character', name: 'Alice', properties: {} }
            },
            edges: [
                { source: playerNodeId, target: 'new_room', type: 'in', properties: {} }
            ]
        },
        turn_events: [],
        time_ticks: 2
    };

    assertTrue(state.applyRuntimeSnapshot(snapshot), 'applies a focused snapshot');
    assertEq(state.data.players.Alice.current_area, 'New Room', 'updates the focused player');
    assertEq(state.data.graph.nodes.distant.name, 'Distant', 'retains unrelated world nodes');
    assertEq(state.data.graph.edges, [
        { source: 'distant', target: 'distant', type: 'loop', properties: {} },
        { source: playerNodeId, target: 'new_room', type: 'in', properties: {} }
    ], 'replaces the old player location and retains unrelated edges');
    assertEq({ type: typeof state.data.areas, keys: Object.keys(state.data.areas || {}) },
        { type: 'object', keys: ['Old Room', 'New Room'] }, 'merges the focused area lookup');
    assertEq(state.data.areas['New Room'].id, 'new_room', 'merges the focused area projection');
    assertEq(state.data.turn_events, [], 'publishes focused turn events');
    assertEq(state.data.time_ticks, 2, 'updates global clock metadata');
});

test('focused turn-cycle refresh uses the scoped snapshot, not a full-world fetch', async () => {
    const state = worldState;
    const previous = {
        runtimeFocus: state._runtimeFocus,
        fetch: state.fetch,
        fetchRuntime: state.fetchRuntime,
        api: window.ApiClient,
        agent: VW.agent,
        turnBased: config.turnBased
    };
    let fullFetches = 0;
    let focusedFetches = 0;
    state._runtimeFocus = ['character/alice'];
    state.fetch = async () => { fullFetches += 1; };
    state.fetchRuntime = async () => { focusedFetches += 1; };
    window.ApiClient = {
        applyTurn: async () => {},
        clearTurnEvents: async () => {}
    };
    VW.agent = { turnNumber: 0 };
    config.turnBased = true;

    try {
        await window.TurnQueue.endTurn();
        assertEq(focusedFetches, 1, 'refreshes the focused working set after the tick');
        assertEq(fullFetches, 0, 'does not request the whole world');
    } finally {
        state._runtimeFocus = previous.runtimeFocus;
        state.fetch = previous.fetch;
        state.fetchRuntime = previous.fetchRuntime;
        if (previous.api === undefined) delete window.ApiClient;
        else window.ApiClient = previous.api;
        VW.agent = previous.agent;
        config.turnBased = previous.turnBased;
    }
});

test('a failed focused runtime request is surfaced and does not install a partial snapshot', async () => {
    const state = new WorldState();
    const previousRuntime = { snapshot_type: 'character_runtime', players: { Alice: {} } };
    state.runtimeData = previousRuntime;
    const originalFetch = window.fetch;
    window.fetch = () => Promise.resolve({
        ok: false,
        status: 409,
        json: async () => ({ error: 'Character scope is not loaded' })
    });

    try {
        let thrown = null;
        try {
            await state.fetchRuntime(['character/alice']);
        } catch (error) {
            thrown = error;
        }
        assertTrue(thrown instanceof Error, 'rejects the failed request');
        assertEq(thrown.message, 'Character scope is not loaded', 'preserves the server error');
        assertEq(state.runtimeData, previousRuntime, 'does not overwrite the last valid snapshot');
    } finally {
        if (originalFetch === undefined) delete window.fetch;
        else window.fetch = originalFetch;
    }
});

test('a focused response arriving after focus clears cannot reinstall stale runtime state', async () => {
    const state = new WorldState();
    state.setRuntimeFocus(['character/alice']);
    const originalFetch = window.fetch;
    let resolveResponse;
    window.fetch = () => new Promise(resolve => { resolveResponse = resolve; });

    try {
        const pending = state.fetchRuntime();
        await Promise.resolve();
        state.setRuntimeFocus([]);
        resolveResponse({
            ok: true,
            json: async () => ({
                snapshot_type: 'character_runtime',
                character_ids: ['character/alice'],
                players: { Alice: {} }
            })
        });
        await pending;
        assertEq(state.runtimeData, null, 'ignores the no-longer-focused response');
    } finally {
        if (originalFetch === undefined) delete window.fetch;
        else window.fetch = originalFetch;
    }
});

test('applyNodeDelta updates cached node in place without refetching', () => {
    const state = new WorldState();
    state.data = {
        graph: {
            nodes: {
                item_sword: { id: 'item_sword', name: 'Iron Sword', properties: { damage: '1d6' } }
            },
            edges: []
        }
    };
    let emitted = null;
    state.on('update', (data) => { emitted = data; });

    const updatedNode = { id: 'item_sword', name: 'Flaming Sword', properties: { damage: '2d6' } };
    const success = state.applyNodeDelta('item_sword', updatedNode);

    assertTrue(success, 'delta was applied');
    assertEq(state.data.graph.nodes.item_sword.name, 'Flaming Sword', 'node name updated');
    assertEq(state.data.graph.nodes.item_sword.properties.damage, '2d6', 'properties updated');
    assertEq(emitted, state.data, 'state update event fired');
});

test('state fetch with 304 Not Modified preserves cached state', async () => {
    const state = new WorldState();
    state.data = { players: { Hero: { HP: 100 } } };
    state._lastEtag = '"rev-42"';

    const originalFetch = window.fetch;
    let sentHeaders = null;
    window.fetch = (url, options) => {
        sentHeaders = options?.headers;
        return Promise.resolve({
            status: 304,
            headers: { get: () => '"rev-42"' }
        });
    };

    try {
        const result = await state.fetch();
        assertEq(sentHeaders['If-None-Match'], '"rev-42"', 'If-None-Match header was sent');
        assertEq(result, state.data, 'returns cached data on 304');
        assertEq(result.players.Hero.HP, 100, 'cached state is preserved');
    } finally {
        if (originalFetch === undefined) delete window.fetch;
        else window.fetch = originalFetch;
    }
});
